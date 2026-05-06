"""Excavator agent — bidder bundle → typed Evidence Graph.

Spec: docs/01-solution.md §4 Pillar 3 + docs/04-document-pipeline.md.

Pipeline per document:
  1. Parse via the W1 ingestion pipeline (typed-pdf / scanned / photo / docx / xlsx).
  2. Render the page-block list as a single, page-marked text body.
  3. Call the field extractor LLM with structured output enforcement
     (`DocumentExtraction`).
  4. For each emitted `FieldValue`:
        * realign `source_quote` to the OCR/typed text → bbox
        * normalise the raw value (Indian numbers, FY, dates, GSTIN, …)
        * compute `final_conf = min(ocr_conf, extractor_conf, provenance_match_conf)`
        * persist as `EvidenceNode`
  5. Append a `bidder.document.excavated` event to the audit ledger.

After all documents are processed the EvidenceGraph aggregator can compute
per-field cross-document agreement.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from pramaan.agents.extractor import (
    AlignedField,
    DocumentExtraction,
    align_to_blocks,
)
from pramaan.config import settings
from pramaan.db.models import Bidder, Document, EvidenceNode
from pramaan.dsl.types import CriterionDSL
from pramaan.ingestion import PageBlock, parse
from pramaan.ledger.chain import get_ledger
from pramaan.llm.client import LLMResult, get_llm_client
from pramaan.prompts import excavator as prompt
from pramaan.storage.blob import get_blob_store

log = logging.getLogger(__name__)


@dataclass
class ExcavateDocumentResult:
    document_id: uuid.UUID
    n_nodes: int
    n_dropped_no_provenance: int
    document_kind: str
    model: str
    prompt_hash: str
    run_id: uuid.UUID


@dataclass
class ExcavateBidderResult:
    bidder_id: uuid.UUID
    documents: list[ExcavateDocumentResult]

    @property
    def total_nodes(self) -> int:
        return sum(d.n_nodes for d in self.documents)


class Excavator:
    """Per-bidder orchestrator. One instance == one bidder run."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.llm = get_llm_client()
        self.blob = get_blob_store()
        self.ledger = get_ledger(session)

    # ── public ────────────────────────────────────────────────────────────

    def excavate_bidder(
        self, bidder: Bidder, dsl: CriterionDSL, *, actor: str
    ) -> ExcavateBidderResult:
        results: list[ExcavateDocumentResult] = []
        for doc in bidder.documents:
            results.append(self.excavate_document(bidder, doc, dsl, actor=actor))
        self.session.commit()
        return ExcavateBidderResult(bidder_id=bidder.id, documents=results)

    def excavate_document(
        self,
        bidder: Bidder,
        document: Document,
        dsl: CriterionDSL,
        *,
        actor: str,
    ) -> ExcavateDocumentResult:
        log.info("excavator.run starting (bidder=%s, document=%s)", bidder.id, document.id)
        run_id = uuid.uuid4()

        data = self.blob.get(key=document.storage_uri)
        cls, blocks = parse(document.filename, data)
        log.info(
            "excavator parsed %s as %s with %d blocks", document.filename, cls, len(blocks)
        )

        body = _render_body(blocks)
        if not body.strip():
            # Nothing to extract — record an empty extraction event so the
            # ledger reflects that we tried, and return.
            self.ledger.append(
                kind="bidder.document.excavated",
                actor=actor,
                tender_id=bidder.tender_id,
                bidder_id=bidder.id,
                payload={
                    "document_id": str(document.id),
                    "n_nodes": 0,
                    "n_dropped_no_provenance": 0,
                    "document_kind": "unknown",
                    "doc_class": cls.value,
                    "n_blocks": 0,
                    "run_id": str(run_id),
                    "reason": "no_text",
                },
            )
            return ExcavateDocumentResult(
                document_id=document.id,
                n_nodes=0,
                n_dropped_no_provenance=0,
                document_kind="unknown",
                model="(none)",
                prompt_hash="",
                run_id=run_id,
            )

        expected_fields = _expected_fields_for(document.filename, dsl)

        result: LLMResult[DocumentExtraction] = self.llm.extract(
            response_model=DocumentExtraction,
            system=prompt.SYSTEM,
            user=prompt.user_prompt(
                doc_filename=document.filename,
                doc_text=body,
                expected_fields=expected_fields,
            ),
            model=settings.llm_extractor_model,
            prompt_template_version=prompt.VERSION,
        )

        extraction = result.value
        # Drop any prior EvidenceNode rows for this (bidder, document) so
        # re-runs are idempotent. The audit ledger preserves history.
        self.session.execute(
            EvidenceNode.__table__.delete().where(
                (EvidenceNode.bidder_id == bidder.id)
                & (EvidenceNode.document_id == document.id)
            )
        )

        n_kept = 0
        n_dropped = 0
        kept_summaries: list[dict] = []
        for fv in extraction.fields:
            aligned = align_to_blocks(fv, blocks)
            if aligned is None:
                log.warning(
                    "dropping ungrounded field=%s value=%r quote=%r",
                    fv.field, fv.value, fv.source_quote,
                )
                n_dropped += 1
                continue
            if aligned.normalised is None and fv.value is not None:
                # Normalisation failed (e.g. malformed GSTIN). Drop.
                log.info(
                    "dropping unnormalisable field=%s raw=%r", fv.field, fv.value
                )
                n_dropped += 1
                continue

            self._persist_node(
                bidder=bidder,
                document=document,
                aligned=aligned,
                run_id=run_id,
                extractor_model=result.model,
                prompt_hash=result.prompt_hash,
            )
            n_kept += 1
            kept_summaries.append({
                "field": fv.field,
                "value": _json_safe(aligned.normalised),
                "fy": fv.fy,
                "page": aligned.block.page,
                "extractor_conf": fv.extractor_confidence,
                "provenance_match_conf": aligned.provenance_match_conf,
            })

        self.session.flush()

        self.ledger.append(
            kind="bidder.document.excavated",
            actor=actor,
            tender_id=bidder.tender_id,
            bidder_id=bidder.id,
            payload={
                "document_id": str(document.id),
                "document_filename": document.filename,
                "document_sha256": document.sha256.hex(),
                "document_kind": extraction.document_kind,
                "doc_class": cls.value,
                "n_blocks": len(blocks),
                "n_nodes": n_kept,
                "n_dropped_no_provenance": n_dropped,
                "model": result.model,
                "prompt_hash": result.prompt_hash,
                "run_id": str(run_id),
                "kept": kept_summaries,
            },
        )

        log.info(
            "excavator.run done (document=%s, kept=%d, dropped=%d)",
            document.id, n_kept, n_dropped,
        )

        return ExcavateDocumentResult(
            document_id=document.id,
            n_nodes=n_kept,
            n_dropped_no_provenance=n_dropped,
            document_kind=extraction.document_kind,
            model=result.model,
            prompt_hash=result.prompt_hash,
            run_id=run_id,
        )

    # ── internals ─────────────────────────────────────────────────────────

    def _persist_node(
        self,
        *,
        bidder: Bidder,
        document: Document,
        aligned: AlignedField,
        run_id: uuid.UUID,
        extractor_model: str,
        prompt_hash: str,
    ) -> EvidenceNode:
        block = aligned.block
        fv = aligned.raw

        ocr_conf = float(block.ocr_conf if block.ocr_conf is not None else 1.0)
        ext_conf = float(fv.extractor_confidence)
        prov_conf = float(aligned.provenance_match_conf)
        # Multiply normalisation confidence in too — a malformed GSTIN that
        # somehow slipped through as None-but-present would pull conf down.
        norm_conf = float(aligned.normalisation_conf)
        final_conf = min(ocr_conf, ext_conf, prov_conf, norm_conf)

        node = EvidenceNode(
            bidder_id=bidder.id,
            document_id=document.id,
            field=fv.field,
            value=_json_safe(aligned.normalised),
            unit=fv.unit,
            fy=fv.fy,
            page=block.page,
            bbox=list(block.bbox),
            ocr_conf=ocr_conf,
            extractor_conf=ext_conf,
            provenance_match_conf=prov_conf,
            final_conf=max(0.0, min(1.0, final_conf)),
            extractor_model=extractor_model,
            extractor_prompt_hash=prompt_hash,
            source_text_sha256=bytes.fromhex(block.source_text_sha256)
            if block.source_text_sha256
            else hashlib.sha256(block.text.encode("utf-8")).digest(),
            source_quote=fv.source_quote[:1000],
        )
        self.session.add(node)
        return node


# ─── Helpers ──────────────────────────────────────────────────────────────


def _render_body(blocks: list[PageBlock]) -> str:
    """Concat blocks into a single string with page markers for the LLM."""
    if not blocks:
        return ""
    lines: list[str] = []
    last_page = -1
    for b in blocks:
        if b.page != last_page:
            lines.append(f"\n[PAGE {b.page}]\n")
            last_page = b.page
        lines.append(b.text)
    return "\n".join(lines).strip()


def _expected_fields_for(filename: str, dsl: CriterionDSL) -> list[str]:
    """Best-effort list of fields the LLM should look for in this doc.

    We crawl the DSL's `evidence_vocabulary`: any entry whose name or
    aliases substring-match the filename contributes its `expected_fields`.
    The LLM treats this as a hint, not a constraint — it's still expected
    to emit anything else relevant it sees.
    """
    name = filename.lower()
    out: set[str] = set()
    for canonical, entry in dsl.evidence_vocabulary.items():
        haystack = [canonical.lower(), *(a.lower() for a in entry.aliases)]
        if any(_filename_hits(name, h) for h in haystack):
            out.update(entry.expected_fields)
    return sorted(out)


def _filename_hits(filename: str, hint: str) -> bool:
    """Loose 'does this filename look like this evidence kind' check."""
    parts = [p for p in hint.replace("-", " ").replace("_", " ").split() if p]
    if not parts:
        return False
    hits = sum(1 for p in parts if p in filename)
    return hits / len(parts) >= 0.5


def _json_safe(value):
    """Coerce SQLAlchemy/JSONB-bound primitives. Identity on basic types."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return str(value)


__all__ = [
    "Excavator",
    "ExcavateBidderResult",
    "ExcavateDocumentResult",
]
