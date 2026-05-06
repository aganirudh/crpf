"""Tender HTTP API.

POST   /tenders                       upload a tender PDF
POST   /tenders/{id}/cartograph       run the Cartographer
GET    /tenders/{id}                  fetch tender + DSL summary
GET    /tenders/{id}/dsl              fetch the CriterionDSL
PATCH  /tenders/{id}/dsl              officer overrides / confirms the DSL
GET    /tenders/{id}/source           stream the original tender PDF (for the right-pane viewer)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import pypdf
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from pramaan.agents.cartographer import Cartographer
from pramaan.auth import CurrentOfficer, get_current_officer
from pramaan.db.models import CriterionDSLRow, Tender
from pramaan.db.session import get_db
from pramaan.dsl.types import CriterionDSL
from pramaan.ingestion.router import classify
from pramaan.ledger.chain import get_ledger
from pramaan.storage.blob import get_blob_store

log = logging.getLogger(__name__)
router = APIRouter(prefix="/tenders", tags=["tenders"])


# ─── Schemas ──────────────────────────────────────────────────────────────


class TenderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference_no: str | None
    department: str | None
    filename: str
    sha256_hex: str
    page_count: int | None
    classification: str | None
    has_dsl: bool


class DSLEnvelope(BaseModel):
    dsl: dict[str, Any]
    dsl_sha256_hex: str
    dsl_version: str
    source_model: str
    source_prompt_hash: str
    reviewed_by: str | None
    reviewed_at: str | None


class CartographResponse(BaseModel):
    tender_id: uuid.UUID
    n_criteria: int
    model: str
    prompt_hash: str


# ─── Routes ───────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TenderSummary)
def upload_tender(
    file: UploadFile,
    background: BackgroundTasks,
    reference_no: str | None = None,
    department: str | None = None,
    db: Session = Depends(get_db),
    me: CurrentOfficer = Depends(get_current_officer),
) -> TenderSummary:
    if file.filename is None or file.size is None:
        raise HTTPException(status_code=400, detail="missing file")
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")

    blob = get_blob_store()
    storage_uri, sha = blob.put(
        namespace="tender",
        filename=file.filename,
        data=data,
        content_type=file.content_type or "application/octet-stream",
    )

    existing = db.execute(select(Tender).where(Tender.sha256 == sha)).scalar_one_or_none()
    if existing is not None:
        return _to_summary(existing, has_dsl=existing.dsl is not None)

    cls = classify(file.filename, data)
    page_count = _safe_page_count(data) if cls.value.endswith("pdf") else None

    tender = Tender(
        reference_no=reference_no,
        department=department,
        filename=file.filename,
        sha256=sha,
        storage_uri=storage_uri,
        page_count=page_count,
        classification=cls.value,
        uploaded_by_id=uuid.UUID(me.id),
    )
    db.add(tender)
    db.flush()

    ledger = get_ledger(db)
    ledger.append(
        kind="tender.uploaded",
        actor=me.external_id,
        tender_id=tender.id,
        payload={
            "tender_id": str(tender.id),
            "filename": file.filename,
            "sha256": sha.hex(),
            "page_count": page_count,
            "classification": cls.value,
        },
    )
    db.commit()
    db.refresh(tender)

    background.add_task(_run_cartographer_async, tender_id=tender.id, actor=me.external_id)
    return _to_summary(tender, has_dsl=False)


@router.post("/{tender_id}/cartograph", response_model=CartographResponse)
def cartograph(
    tender_id: uuid.UUID,
    db: Session = Depends(get_db),
    me: CurrentOfficer = Depends(get_current_officer),
) -> CartographResponse:
    tender = db.get(Tender, tender_id) or _404(tender_id)
    cart = Cartographer(db)
    out = cart.run(tender, actor=me.external_id)
    return CartographResponse(
        tender_id=tender_id,
        n_criteria=len(out.dsl.criteria),
        model=out.model,
        prompt_hash=out.prompt_hash,
    )


@router.get("/{tender_id}", response_model=TenderSummary)
def get_tender(tender_id: uuid.UUID, db: Session = Depends(get_db)) -> TenderSummary:
    tender = db.get(Tender, tender_id) or _404(tender_id)
    return _to_summary(tender, has_dsl=tender.dsl is not None)


@router.get("/{tender_id}/dsl", response_model=DSLEnvelope)
def get_dsl(tender_id: uuid.UUID, db: Session = Depends(get_db)) -> DSLEnvelope:
    row = db.get(CriterionDSLRow, tender_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail="DSL not yet extracted; POST /tenders/{id}/cartograph first."
        )
    return DSLEnvelope(
        dsl=row.dsl,
        dsl_sha256_hex=row.dsl_sha256.hex(),
        dsl_version=row.dsl_version,
        source_model=row.source_model,
        source_prompt_hash=row.source_prompt_hash,
        reviewed_by=str(row.reviewed_by_id) if row.reviewed_by_id else None,
        reviewed_at=row.reviewed_at.isoformat() if row.reviewed_at else None,
    )


@router.patch("/{tender_id}/dsl", response_model=DSLEnvelope)
def patch_dsl(
    tender_id: uuid.UUID,
    dsl: dict[str, Any],
    db: Session = Depends(get_db),
    me: CurrentOfficer = Depends(get_current_officer),
) -> DSLEnvelope:
    """Officer-confirmed DSL replaces the model-extracted DSL.

    The submitted DSL is validated against the schema before persisting.
    The change is appended to the audit ledger as `dsl.confirmed`.
    """
    import hashlib
    from datetime import UTC, datetime

    from pramaan.ledger.chain import canonical_json

    parsed = CriterionDSL.model_validate(dsl)
    row = db.get(CriterionDSLRow, tender_id)
    if row is None:
        raise HTTPException(status_code=404, detail="DSL not found; cartograph first.")

    new_json = parsed.model_dump(mode="json")
    new_sha = hashlib.sha256(canonical_json(new_json).encode("utf-8")).digest()
    old_sha_hex = row.dsl_sha256.hex()

    row.dsl = new_json
    row.dsl_sha256 = new_sha
    row.reviewed_by_id = uuid.UUID(me.id)
    row.reviewed_at = datetime.now(UTC)

    ledger = get_ledger(db)
    ledger.append(
        kind="dsl.confirmed",
        actor=me.external_id,
        tender_id=tender_id,
        payload={
            "tender_id": str(tender_id),
            "old_dsl_sha256": old_sha_hex,
            "new_dsl_sha256": new_sha.hex(),
            "n_criteria": len(parsed.criteria),
        },
    )
    db.commit()
    db.refresh(row)
    return DSLEnvelope(
        dsl=row.dsl,
        dsl_sha256_hex=row.dsl_sha256.hex(),
        dsl_version=row.dsl_version,
        source_model=row.source_model,
        source_prompt_hash=row.source_prompt_hash,
        reviewed_by=str(row.reviewed_by_id) if row.reviewed_by_id else None,
        reviewed_at=row.reviewed_at.isoformat() if row.reviewed_at else None,
    )


@router.get("/{tender_id}/source")
def stream_source(tender_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    tender = db.get(Tender, tender_id) or _404(tender_id)
    blob = get_blob_store()
    data = blob.get(key=tender.storage_uri)

    def _gen():
        yield data

    return StreamingResponse(
        _gen(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{tender.filename}"'},
    )


# ─── Helpers ──────────────────────────────────────────────────────────────


def _to_summary(t: Tender, *, has_dsl: bool) -> TenderSummary:
    return TenderSummary(
        id=t.id,
        reference_no=t.reference_no,
        department=t.department,
        filename=t.filename,
        sha256_hex=t.sha256.hex(),
        page_count=t.page_count,
        classification=t.classification,
        has_dsl=has_dsl,
    )


def _404(tender_id: uuid.UUID) -> Tender:
    raise HTTPException(status_code=404, detail=f"tender {tender_id} not found")


def _safe_page_count(data: bytes) -> int | None:
    import io

    try:
        return len(pypdf.PdfReader(io.BytesIO(data)).pages)
    except Exception:
        return None


def _run_cartographer_async(*, tender_id: uuid.UUID, actor: str) -> None:
    """Background task entry — opens its own session."""
    from pramaan.db.session import session_scope

    try:
        with session_scope() as db:
            tender = db.get(Tender, tender_id)
            if tender is None:
                return
            Cartographer(db).run(tender, actor=actor)
    except Exception:
        log.exception("background cartographer failed for %s", tender_id)
