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

        body = _render_body(blocks)

        result: LLMResult[CriterionDSL] = self.llm.extract(
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

        dsl = result.value
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
                "model": result.model,
                "prompt_hash": result.prompt_hash,
                "run_id": str(run_id),
                "n_criteria": len(dsl.criteria),
                "doc_class": cls.value,
                "n_blocks": len(blocks),
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
            dsl=dsl, run_id=run_id, model=result.model, prompt_hash=result.prompt_hash
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
