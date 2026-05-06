"""Bidder HTTP API.

Endpoints:
  POST   /tenders/{tid}/bidders                       create a bidder
  GET    /tenders/{tid}/bidders                       list bidders
  GET    /bidders/{bid}                               fetch one bidder
  POST   /bidders/{bid}/documents                     upload a document
  GET    /bidders/{bid}/documents                     list documents
  GET    /bidders/{bid}/documents/{did}/source        stream document for viewer
  POST   /bidders/{bid}/excavate                      run the Excavator (W3)
  POST   /bidders/{bid}/documents/{did}/excavate      run for a single doc
  GET    /bidders/{bid}/evidence-graph                aggregated graph view
  GET    /bidders/{bid}/evidence-nodes                flat node list
"""

from __future__ import annotations

import io
import logging
import uuid
from typing import Any

import pypdf
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from pramaan.agents.evidence_graph import build_evidence_graph
from pramaan.agents.excavator import Excavator
from pramaan.auth import CurrentOfficer, get_current_officer
from pramaan.db.models import Bidder, CriterionDSLRow, Document, EvidenceNode, Tender
from pramaan.db.session import get_db
from pramaan.dsl.types import CriterionDSL
from pramaan.ingestion.router import classify
from pramaan.ledger.chain import get_ledger
from pramaan.storage.blob import get_blob_store

log = logging.getLogger(__name__)
router = APIRouter(tags=["bidders"])


# ─── Schemas ──────────────────────────────────────────────────────────────


class BidderIn(BaseModel):
    legal_name: str | None = None
    cin: str | None = None
    gstin: str | None = None
    pan: str | None = None
    bid_price_inr: int | None = None


class BidderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tender_id: uuid.UUID
    legal_name: str | None
    cin: str | None
    gstin: str | None
    pan: str | None
    bid_price_inr: int | None
    n_documents: int


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bidder_id: uuid.UUID
    filename: str
    mime: str
    sha256_hex: str
    page_count: int | None
    classification: str | None
    n_evidence_nodes: int = 0
    excavated: bool = False
    document_kind: str | None = None


class EvidenceNodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bidder_id: uuid.UUID
    document_id: uuid.UUID
    field: str
    value: Any
    unit: str | None
    fy: str | None
    page: int
    bbox: list[float]
    ocr_conf: float | None
    extractor_conf: float | None
    provenance_match_conf: float | None
    final_conf: float
    extractor_model: str
    source_quote: str | None


class FieldSourceOut(BaseModel):
    node_id: uuid.UUID
    document_id: uuid.UUID
    value: Any
    page: int
    bbox: list[float]
    final_conf: float
    extractor_conf: float
    ocr_conf: float
    provenance_match_conf: float
    source_quote: str | None


class FieldAggregateOut(BaseModel):
    field: str
    fy: str | None
    value: Any
    sources: list[FieldSourceOut]
    agreement_score: float
    final_conf: float
    cross_doc_disagreement: bool


class EvidenceGraphOut(BaseModel):
    bidder_id: uuid.UUID
    n_documents: int
    n_nodes: int
    fields: list[FieldAggregateOut]


class ExcavateResultOut(BaseModel):
    bidder_id: uuid.UUID
    documents: list[dict]
    total_nodes: int


# ─── Bidder routes ────────────────────────────────────────────────────────


@router.post(
    "/tenders/{tender_id}/bidders",
    status_code=status.HTTP_201_CREATED,
    response_model=BidderSummary,
)
def create_bidder(
    tender_id: uuid.UUID,
    payload: BidderIn,
    db: Session = Depends(get_db),
    me: CurrentOfficer = Depends(get_current_officer),
) -> BidderSummary:
    tender = db.get(Tender, tender_id) or _404("tender", tender_id)
    bidder = Bidder(tender_id=tender.id, **payload.model_dump())
    db.add(bidder)
    db.flush()
    get_ledger(db).append(
        kind="bidder.created",
        actor=me.external_id,
        tender_id=tender.id,
        bidder_id=bidder.id,
        payload={"bidder_id": str(bidder.id), **payload.model_dump()},
    )
    db.commit()
    db.refresh(bidder)
    return _bidder_summary(bidder, n_docs=0)


@router.get("/tenders/{tender_id}/bidders", response_model=list[BidderSummary])
def list_bidders(tender_id: uuid.UUID, db: Session = Depends(get_db)) -> list[BidderSummary]:
    bidders = db.execute(select(Bidder).where(Bidder.tender_id == tender_id)).scalars().all()
    return [_bidder_summary(b, n_docs=len(b.documents)) for b in bidders]


@router.get("/bidders/{bidder_id}", response_model=BidderSummary)
def get_bidder(bidder_id: uuid.UUID, db: Session = Depends(get_db)) -> BidderSummary:
    bidder = db.get(Bidder, bidder_id) or _404("bidder", bidder_id)
    return _bidder_summary(bidder, n_docs=len(bidder.documents))


# ─── Document routes ──────────────────────────────────────────────────────


@router.post(
    "/bidders/{bidder_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentSummary,
)
def upload_document(
    bidder_id: uuid.UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    me: CurrentOfficer = Depends(get_current_officer),
) -> DocumentSummary:
    bidder = db.get(Bidder, bidder_id) or _404("bidder", bidder_id)
    if file.filename is None:
        raise HTTPException(status_code=400, detail="missing file")
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")

    blob = get_blob_store()
    storage_uri, sha = blob.put(
        namespace=f"bidder/{bidder.id}",
        filename=file.filename,
        data=data,
        content_type=file.content_type or "application/octet-stream",
    )
    cls = classify(file.filename, data)
    page_count = _safe_page_count(data) if cls.value.endswith("pdf") else None

    existing = db.execute(
        select(Document).where(Document.bidder_id == bidder.id, Document.sha256 == sha)
    ).scalar_one_or_none()
    if existing is not None:
        return _doc_summary(existing)

    doc = Document(
        bidder_id=bidder.id,
        filename=file.filename,
        mime=file.content_type or "application/octet-stream",
        sha256=sha,
        storage_uri=storage_uri,
        page_count=page_count,
        classification=cls.value,
    )
    db.add(doc)
    db.flush()
    get_ledger(db).append(
        kind="bidder.document.uploaded",
        actor=me.external_id,
        tender_id=bidder.tender_id,
        bidder_id=bidder.id,
        payload={
            "document_id": str(doc.id),
            "filename": file.filename,
            "sha256": sha.hex(),
            "page_count": page_count,
            "classification": cls.value,
        },
    )
    db.commit()
    db.refresh(doc)
    return _doc_summary(doc)


@router.get("/bidders/{bidder_id}/documents", response_model=list[DocumentSummary])
def list_documents(bidder_id: uuid.UUID, db: Session = Depends(get_db)) -> list[DocumentSummary]:
    docs = db.execute(select(Document).where(Document.bidder_id == bidder_id)).scalars().all()
    counts = _evidence_counts_by_document(db, bidder_id)
    kinds = _document_kinds(db, bidder_id)
    return [
        _doc_summary(d, n_nodes=counts.get(d.id, 0), document_kind=kinds.get(d.id))
        for d in docs
    ]


@router.get("/bidders/{bidder_id}/documents/{document_id}/source")
def stream_document(
    bidder_id: uuid.UUID, document_id: uuid.UUID, db: Session = Depends(get_db)
) -> Response:
    doc = db.get(Document, document_id)
    if doc is None or doc.bidder_id != bidder_id:
        raise HTTPException(status_code=404, detail="document not found")
    blob = get_blob_store()
    data = blob.get(key=doc.storage_uri)

    def _gen():
        yield data

    return StreamingResponse(
        _gen(),
        media_type=doc.mime,
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )


# ─── Excavator routes (W3) ────────────────────────────────────────────────


@router.post("/bidders/{bidder_id}/excavate", response_model=ExcavateResultOut)
def excavate_bidder(
    bidder_id: uuid.UUID,
    background: BackgroundTasks,
    foreground: bool = False,
    db: Session = Depends(get_db),
    me: CurrentOfficer = Depends(get_current_officer),
) -> ExcavateResultOut:
    """Run the Excavator over every document the bidder has uploaded.

    By default the run is queued as a background task and the response is
    a placeholder summary; pass `?foreground=true` to block until the run
    completes (useful in tests and the demo flow).
    """
    bidder = db.get(Bidder, bidder_id) or _404("bidder", bidder_id)
    dsl = _load_dsl_or_404(db, bidder.tender_id)

    if foreground:
        excavator = Excavator(db)
        result = excavator.excavate_bidder(bidder, dsl, actor=me.external_id)
        return ExcavateResultOut(
            bidder_id=bidder.id,
            documents=[_doc_result_payload(r) for r in result.documents],
            total_nodes=result.total_nodes,
        )

    background.add_task(
        _run_excavator_async, bidder_id=bidder.id, actor=me.external_id
    )
    return ExcavateResultOut(bidder_id=bidder.id, documents=[], total_nodes=0)


@router.post(
    "/bidders/{bidder_id}/documents/{document_id}/excavate",
    response_model=DocumentSummary,
)
def excavate_document(
    bidder_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    me: CurrentOfficer = Depends(get_current_officer),
) -> DocumentSummary:
    bidder = db.get(Bidder, bidder_id) or _404("bidder", bidder_id)
    document = db.get(Document, document_id)
    if document is None or document.bidder_id != bidder.id:
        raise HTTPException(status_code=404, detail="document not found")
    dsl = _load_dsl_or_404(db, bidder.tender_id)

    excavator = Excavator(db)
    result = excavator.excavate_document(bidder, document, dsl, actor=me.external_id)
    db.commit()
    return _doc_summary(
        document, n_nodes=result.n_nodes, document_kind=result.document_kind
    )


@router.get(
    "/bidders/{bidder_id}/evidence-graph", response_model=EvidenceGraphOut
)
def get_evidence_graph(bidder_id: uuid.UUID, db: Session = Depends(get_db)) -> EvidenceGraphOut:
    bidder = db.get(Bidder, bidder_id) or _404("bidder", bidder_id)
    view = build_evidence_graph(db, bidder.id)
    fields_out = [
        FieldAggregateOut(
            field=a.field,
            fy=a.fy,
            value=a.value,
            sources=[
                FieldSourceOut(
                    node_id=s.node_id,
                    document_id=s.document_id,
                    value=s.value,
                    page=s.page,
                    bbox=list(s.bbox),
                    final_conf=s.final_conf,
                    extractor_conf=s.extractor_conf,
                    ocr_conf=s.ocr_conf,
                    provenance_match_conf=s.provenance_match_conf,
                    source_quote=s.source_quote,
                )
                for s in a.sources
            ],
            agreement_score=a.agreement_score,
            final_conf=a.final_conf,
            cross_doc_disagreement=a.cross_doc_disagreement,
        )
        for a in view.fields
    ]
    n_nodes = sum(a.n_sources for a in view.fields)
    return EvidenceGraphOut(
        bidder_id=bidder.id,
        n_documents=len(bidder.documents),
        n_nodes=n_nodes,
        fields=fields_out,
    )


@router.get(
    "/bidders/{bidder_id}/evidence-nodes", response_model=list[EvidenceNodeOut]
)
def list_evidence_nodes(bidder_id: uuid.UUID, db: Session = Depends(get_db)) -> list[EvidenceNodeOut]:
    rows = db.execute(
        select(EvidenceNode).where(EvidenceNode.bidder_id == bidder_id).order_by(
            EvidenceNode.field, EvidenceNode.fy
        )
    ).scalars().all()
    return [_evidence_node_out(n) for n in rows]


# ─── Helpers ──────────────────────────────────────────────────────────────


def _bidder_summary(b: Bidder, *, n_docs: int) -> BidderSummary:
    return BidderSummary(
        id=b.id,
        tender_id=b.tender_id,
        legal_name=b.legal_name,
        cin=b.cin,
        gstin=b.gstin,
        pan=b.pan,
        bid_price_inr=b.bid_price_inr,
        n_documents=n_docs,
    )


def _doc_summary(
    d: Document, *, n_nodes: int = 0, document_kind: str | None = None
) -> DocumentSummary:
    return DocumentSummary(
        id=d.id,
        bidder_id=d.bidder_id,
        filename=d.filename,
        mime=d.mime,
        sha256_hex=d.sha256.hex(),
        page_count=d.page_count,
        classification=d.classification,
        n_evidence_nodes=n_nodes,
        excavated=n_nodes > 0,
        document_kind=document_kind,
    )


def _evidence_node_out(n: EvidenceNode) -> EvidenceNodeOut:
    return EvidenceNodeOut(
        id=n.id,
        bidder_id=n.bidder_id,
        document_id=n.document_id,
        field=n.field,
        value=n.value,
        unit=n.unit,
        fy=n.fy,
        page=n.page,
        bbox=list(n.bbox) if isinstance(n.bbox, list) else list(n.bbox),
        ocr_conf=n.ocr_conf,
        extractor_conf=n.extractor_conf,
        provenance_match_conf=n.provenance_match_conf,
        final_conf=n.final_conf,
        extractor_model=n.extractor_model,
        source_quote=n.source_quote,
    )


def _404(kind: str, ident: uuid.UUID):
    raise HTTPException(status_code=404, detail=f"{kind} {ident} not found")


def _safe_page_count(data: bytes) -> int | None:
    try:
        return len(pypdf.PdfReader(io.BytesIO(data)).pages)
    except Exception:
        return None


def _evidence_counts_by_document(db: Session, bidder_id: uuid.UUID) -> dict[uuid.UUID, int]:
    from sqlalchemy import func
    rows = db.execute(
        select(EvidenceNode.document_id, func.count(EvidenceNode.id))
        .where(EvidenceNode.bidder_id == bidder_id)
        .group_by(EvidenceNode.document_id)
    ).all()
    return {r[0]: int(r[1]) for r in rows}


def _document_kinds(db: Session, bidder_id: uuid.UUID) -> dict[uuid.UUID, str]:
    """Look up the most recent excavated document_kind per document by reading
    the audit ledger. (We don't materialise this on `Document` because the
    same physical document could in theory be re-classified across runs.)"""
    from pramaan.db.models import LedgerEvent
    rows = db.execute(
        select(LedgerEvent)
        .where(LedgerEvent.kind == "bidder.document.excavated")
        .where(LedgerEvent.bidder_id == bidder_id)
        .order_by(LedgerEvent.seq.desc())
    ).scalars().all()
    out: dict[uuid.UUID, str] = {}
    for ev in rows:
        try:
            doc_id = uuid.UUID(ev.payload["document_id"])
        except Exception:
            continue
        if doc_id not in out:
            out[doc_id] = ev.payload.get("document_kind") or "unknown"
    return out


def _load_dsl_or_404(db: Session, tender_id: uuid.UUID) -> CriterionDSL:
    row = db.get(CriterionDSLRow, tender_id)
    if row is None:
        raise HTTPException(
            status_code=409,
            detail="DSL not yet extracted; run the Cartographer for this tender first.",
        )
    return CriterionDSL.model_validate(row.dsl)


def _doc_result_payload(r) -> dict:
    return {
        "document_id": str(r.document_id),
        "n_nodes": r.n_nodes,
        "n_dropped_no_provenance": r.n_dropped_no_provenance,
        "document_kind": r.document_kind,
        "model": r.model,
        "prompt_hash": r.prompt_hash,
        "run_id": str(r.run_id),
    }


def _run_excavator_async(*, bidder_id: uuid.UUID, actor: str) -> None:
    """Background task entry — opens its own session."""
    from pramaan.db.session import session_scope

    try:
        with session_scope() as db:
            bidder = db.get(Bidder, bidder_id)
            if bidder is None:
                return
            row = db.get(CriterionDSLRow, bidder.tender_id)
            if row is None:
                log.warning("excavator skipped: no DSL for tender %s", bidder.tender_id)
                return
            dsl = CriterionDSL.model_validate(row.dsl)
            Excavator(db).excavate_bidder(bidder, dsl, actor=actor)
    except Exception:
        log.exception("background excavator failed for %s", bidder_id)
