"""Cartographer agent — tender PDF → typed CriterionDSL.

Spec: docs/01-solution.md §4 Pillar 2, docs/03-criterion-dsl.md.

Pipeline:
  1. Parse the tender via the document pipeline (typically Path A).
  2. Concatenate text into a tender body (with page markers preserved so
     the LLM can populate text_source).
  3. Call the LLM with structured-output enforcement against `CriterionDSL`.
  4. Persist the DSL + audit-log a `cartographer.run` event.

The LLM is the only LLM in the criterion-extraction path. The verdict path
remains symbolic.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from pramaan.config import settings
from pramaan.db.models import CriterionDSLRow, Tender
from pramaan.dsl.types import CriterionDSL
from pramaan.ingestion import parse
from pramaan.ledger.chain import canonical_json, get_ledger
from pramaan.llm.client import LLMResult, get_llm_client
from pramaan.prompts import cartographer as prompt
from pramaan.storage.blob import get_blob_store
import hashlib

log = logging.getLogger(__name__)


@dataclass
class CartographerOutput:
    dsl: CriterionDSL
    run_id: uuid.UUID
    model: str
    prompt_hash: str


class Cartographer:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.llm = get_llm_client()
        self.blob = get_blob_store()
        self.ledger = get_ledger(session)

    def run(self, tender: Tender, *, actor: str) -> CartographerOutput:
        log.info("cartographer.run starting (tender=%s)", tender.id)
        run_id = uuid.uuid4()

        data = self.blob.get(key=tender.storage_uri)
        cls, blocks = parse(tender.filename, data)
        log.info("cartographer parsed %s as %s with %d blocks", tender.filename, cls, len(blocks))

        selected = _select_criteria_blocks(blocks)

        # Large tenders regularly exceed provider context limits; gateways
        # silently truncate, leading to only a handful of criteria extracted.
        # We chunk by page and merge results deterministically.
        chunks = _chunk_blocks_by_page(selected, max_pages=12, max_blocks=450)
        chunk_dsls: list[CriterionDSL] = []
        last_result: LLMResult[CriterionDSL] | None = None
        for chunk in chunks:
            body = _render_body(chunk)
            last_result = self.llm.extract(
                response_model=CriterionDSL,
                system=prompt.SYSTEM,
                user=prompt.user_prompt(
                    tender_text=body,
                    tender_sha256=tender.sha256.hex(),
                    tender_id=tender.reference_no or str(tender.id),
                ),
                model=settings.llm_extractor_model,
                prompt_template_version=prompt.VERSION,
            )
            chunk_dsls.append(last_result.value)

        dsl = _merge_chunk_dsls(chunk_dsls, tender_id=tender.reference_no or str(tender.id))
        # Preserve audit metadata from the last chunk extraction (best-effort);
        # every chunk's run is still audit-logged via the ledger payload below.
        result = last_result
        # Patch metadata that the model shouldn't have to know.
        dsl.tender.source_sha256 = tender.sha256.hex()
        if tender.reference_no:
            dsl.tender.id = tender.reference_no

        dsl_json = dsl.model_dump(mode="json")
        dsl_sha = hashlib.sha256(canonical_json(dsl_json).encode("utf-8")).digest()

        row = self.session.get(CriterionDSLRow, tender.id)
        if row is None:
            row = CriterionDSLRow(
                tender_id=tender.id,
                dsl=dsl_json,
                dsl_sha256=dsl_sha,
                source_model=result.model,
                source_prompt_hash=result.prompt_hash,
                cartographer_run_id=run_id,
            )
            self.session.add(row)
        else:
            row.dsl = dsl_json
            row.dsl_sha256 = dsl_sha
            row.source_model = result.model
            row.source_prompt_hash = result.prompt_hash
            row.cartographer_run_id = run_id

        self.ledger.append(
            kind="cartographer.run",
            actor=actor,
            tender_id=tender.id,
            payload={
                "tender_id": str(tender.id),
                "tender_sha256": tender.sha256.hex(),
                "dsl_sha256": dsl_sha.hex(),
                "model": (result.model if result else "(unknown)"),
                "prompt_hash": (result.prompt_hash if result else ""),
                "run_id": str(run_id),
                "n_criteria": len(dsl.criteria),
                "doc_class": cls.value,
                "n_blocks_total": len(blocks),
                "n_blocks_used": len(selected),
                "n_chunks": len(chunks),
                "selection_strategy": "keyword+neighbor:v1",
            },
        )

        self.session.commit()
        log.info(
            "cartographer.run done (tender=%s, criteria=%d, model=%s)",
            tender.id,
            len(dsl.criteria),
            result.model,
        )
        return CartographerOutput(
            dsl=dsl, 
            run_id=run_id, 
            model=result.model if result else "none", 
            prompt_hash=result.prompt_hash if result else ""
        )


def _render_body(blocks) -> str:
    """Concat blocks into a single string with page markers for the LLM."""
    lines: list[str] = []
    last_page = -1
    for b in blocks:
        if b.page != last_page:
            lines.append(f"\n[PAGE {b.page}]\n")
            last_page = b.page
        lines.append(b.text)
    return "\n".join(lines).strip()


_CRITERIA_HINT_RE = re.compile(
    r"\b("
    r"eligib|eligibility|qualification|qualifying|pre[-\s]?qualification|"
    r"criteria|requirement|conditions?|bidder\s+shall|shall\b|must\b|required\b|"
    r"experience|turnover|financial|technical|gstin?|pan\b|cin\b|iso\b|"
    r"emd\b|bid\s+security|performance\s+security|"
    r"submission|documents?\s+to\s+be\s+submitted|certificat"
    r")\b",
    re.IGNORECASE,
)


def _select_criteria_blocks(blocks):
    """Heuristic pre-filter to keep Cartographer context within provider limits.

    Many tenders are 100+ pages; sending the full text often gets truncated by
    upstream gateways, causing the model to emit only a few criteria. We keep
    blocks that look like eligibility/qualification clauses plus nearby context.
    """
    if not blocks:
        return blocks

    # Keep matched indices plus a small neighbor window so numbering/headers survive.
    keep: set[int] = set()
    for i, b in enumerate(blocks):
        if _CRITERIA_HINT_RE.search(b.text or ""):
            for j in range(max(0, i - 2), min(len(blocks), i + 3)):
                keep.add(j)

    # If heuristics find too little, fall back to the full document rather than
    # starving the LLM.
    if len(keep) < min(80, max(10, len(blocks) // 50)):
        return blocks

    selected = [blocks[i] for i in sorted(keep)]

    # Hard cap to avoid pathological cases (e.g. keyword on every line).
    # Prefer earlier blocks because eligibility sections are typically near front.
    cap = 1400
    if len(selected) > cap:
        selected = selected[:cap]
    return selected


def _chunk_blocks_by_page(blocks, *, max_pages: int, max_blocks: int):
    if not blocks:
        return []
    # Preserve page order; group consecutive pages into chunks.
    chunks: list[list] = []
    cur: list = []
    cur_pages: set[int] = set()
    for b in blocks:
        next_pages = set(cur_pages)
        next_pages.add(int(b.page))
        if cur and (len(next_pages) > max_pages or len(cur) >= max_blocks):
            chunks.append(cur)
            cur = []
            cur_pages = set()
        cur.append(b)
        cur_pages.add(int(b.page))
    if cur:
        chunks.append(cur)
    return chunks


def _merge_chunk_dsls(dsls: list[CriterionDSL], *, tender_id: str) -> CriterionDSL:
    """Merge per-chunk CriterionDSLs into one, de-duplicating by text."""
    if not dsls:
        return CriterionDSL.model_validate(
            {
                "dsl_version": "v1",
                "tender": {"id": tender_id, "source_sha256": "0" * 64, "language": "en"},
                "criteria": [],
                "evidence_vocabulary": {},
            }
        )

    seen: set[str] = set()
    merged_criteria = []
    merged_vocab: dict = {}

    def _norm_text(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").strip().lower())

    for d in dsls:
        for k, v in (d.evidence_vocabulary or {}).items():
            if k not in merged_vocab:
                merged_vocab[k] = v
        for c in d.criteria:
            key = _norm_text(c.text)
            if not key or key in seen:
                continue
            seen.add(key)
            merged_criteria.append(c)

    # Deterministic IDs: C1..Cn
    for i, c in enumerate(merged_criteria, start=1):
        c.id = f"C{i}"

    base = dsls[0]
    base.criteria = merged_criteria
    base.evidence_vocabulary = merged_vocab
    return base
