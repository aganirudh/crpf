"""Field extractor — the LLM stage that turns text + bboxes into typed evidence.

Spec: docs/04-document-pipeline.md § 8 (the field extractor) and § 10
(confidence). Used by the Excavator (W3) once per document.

Hardening rules (the bits that prevent hallucinated values):

  * Every emitted `FieldValue` carries a `source_quote` that **must** be a
    near-substring of the OCR/typed text on its declared page. Quotes that
    cannot be located within tolerance are rejected.
  * The bbox is realigned to the page block whose text contains the quote.
    The model is never trusted to invent coordinates.
  * `final_conf = min(ocr_conf, extractor_conf, provenance_match_conf)`.
  * If the model's `extractor_confidence` is < the configured T1 *and* no
    cross-document agreement is going to save it, the Excavator routes the
    affected criterion to Manual Review (handled at the aggregator stage).

The schema below is intentionally narrow. The DSL grammar admits just a
handful of canonical fields; every evidence kind (`audited_financial_statement`,
`gst_registration_certificate`, …) maps to one of these field names so the
Adjudicator can apply uniform constraints.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from pramaan.dsl import (
    canonical_entity_name,
    normalise_cin,
    normalise_gstin,
    normalise_pan,
    normalise_udin,
    parse_date_iso,
    parse_fy,
    parse_inr,
)
from pramaan.ingestion import PageBlock

log = logging.getLogger(__name__)


# ─── Field vocabulary ─────────────────────────────────────────────────────


# The closed set of fields the system can reason about today. Extending this
# list is a deliberate decision — it requires both prompt + adjudicator work.
KnownField = Literal[
    "annual_turnover_inr",
    "fy",
    "auditor_name",
    "ca_membership_no",
    "udin",
    "gstin",
    "pan",
    "cin",
    "legal_name",
    "registration_date",
    "iso_certificate_no",
    "iso_issuer",
    "iso_valid_to",
    "iso_standard",
    "epf_registration_no",
    "esi_registration_no",
    "completed_project_name",
    "completed_project_value_inr",
    "completed_project_owner",
    "completion_date",
    "blacklist_declaration_present",
]


# Coarse field → canonical normaliser. Used at extraction time.
def normalise_value(field: str, raw: Any) -> tuple[Any, float]:
    """Normalise a raw value to its canonical form and a small confidence prior.

    Returns `(normalised, confidence)`. Unknown fields pass through untouched.
    """
    if raw is None:
        return None, 1.0

    if field.endswith("_inr"):
        if isinstance(raw, (int, float)) and raw > 0:
            return int(raw), 0.95
        if isinstance(raw, str):
            m = parse_inr(raw)
            if m is None:
                return None, 0.0
            return m.inr, m.confidence

    if field == "fy":
        canonical = parse_fy(str(raw))
        return canonical, 1.0 if canonical else 0.0

    if field == "completion_date" or field == "registration_date" or field == "iso_valid_to":
        canonical = parse_date_iso(str(raw))
        return canonical, 1.0 if canonical else 0.0

    if field == "gstin":
        canonical = normalise_gstin(str(raw))
        return canonical, 1.0 if canonical else 0.0
    if field == "pan":
        canonical = normalise_pan(str(raw))
        return canonical, 1.0 if canonical else 0.0
    if field == "cin":
        canonical = normalise_cin(str(raw))
        return canonical, 1.0 if canonical else 0.0
    if field == "udin":
        canonical = normalise_udin(str(raw))
        return canonical, 1.0 if canonical else 0.0

    if field == "legal_name":
        return canonical_entity_name(str(raw)) or str(raw).strip(), 0.9

    return raw, 1.0


# ─── Models for structured-output extraction ──────────────────────────────


class FieldValue(BaseModel):
    """A single extracted field with provenance.

    The model is *forced* to populate `source_quote` with a substring of
    the text that produced this value. We re-locate that substring against
    OCR blocks to obtain the bbox.
    """

    model_config = ConfigDict(extra="forbid")

    field: str
    value: int | float | str | bool | None
    unit: str | None = None
    fy: str | None = None
    """Optional financial year scope (canonical 'YYYY-YY')."""

    page: int = Field(ge=1)
    source_quote: str = Field(min_length=2)
    """Exact (or near-exact) substring of the document text on `page`."""

    extractor_confidence: float = Field(ge=0.0, le=1.0)


class DocumentExtraction(BaseModel):
    """Multi-field extraction result for one document.

    The same document can yield several values (e.g. an audited FS lists
    turnover for three FYs); the Excavator persists each as its own
    `EvidenceNode`.
    """

    model_config = ConfigDict(extra="forbid")

    document_kind: str
    """E.g. 'audited_financial_statement', 'gst_registration_certificate'.
    May be 'unknown' if the model cannot classify; the criterion DSL still
    drives consumption regardless."""

    fields: list[FieldValue] = Field(default_factory=list)
    notes: str | None = None


# ─── Bbox realignment ─────────────────────────────────────────────────────


@dataclass(slots=True)
class AlignedField:
    """A `FieldValue` plus the OCR block it was matched against."""

    raw: FieldValue
    block: PageBlock
    provenance_match_conf: float
    """Levenshtein-style similarity between source_quote and block text."""

    normalised: Any
    normalisation_conf: float


def align_to_blocks(field: FieldValue, blocks: list[PageBlock]) -> AlignedField | None:
    """Locate `field.source_quote` against the OCR blocks on its page.

    Returns the best-matching block + a similarity score. We require the
    match to clear a low floor (0.55) — anything less and we drop the field
    rather than emit a phantom node.
    """
    same_page = [b for b in blocks if b.page == field.page]
    candidates = same_page or blocks  # if model lied about page, scan all
    if not candidates:
        return None

    needle = field.source_quote.strip().lower()
    if not needle:
        return None

    best: tuple[float, PageBlock] | None = None
    for b in candidates:
        hay = b.text.lower()
        if needle in hay:
            score = 1.0
        elif hay in needle:
            # Block is short; quote contains it. Treat as strong match.
            score = max(0.85, len(hay) / max(1, len(needle)))
        else:
            score = _ratio(needle, hay)
        if best is None or score > best[0]:
            best = (score, b)

    if best is None or best[0] < 0.55:
        return None

    norm_value, norm_conf = normalise_value(field.field, field.value)
    return AlignedField(
        raw=field,
        block=best[1],
        provenance_match_conf=float(best[0]),
        normalised=norm_value,
        normalisation_conf=float(norm_conf),
    )


# ─── Light-weight similarity (no heavy deps) ──────────────────────────────


def _ratio(a: str, b: str) -> float:
    """Cheap normalised similarity in [0, 1]. Hybrid token Jaccard + sliding
    longest-common-substring length over the shorter string. Sufficient for
    re-locating a 5-30 character quote against an OCR line."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    # Token Jaccard on alphanumeric tokens.
    ta = {t for t in _tokens(a) if len(t) > 1}
    tb = {t for t in _tokens(b) if len(t) > 1}
    jaccard = len(ta & tb) / max(1, len(ta | tb)) if (ta or tb) else 0.0

    # Sliding-window character coverage of the shorter string in the longer.
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    n = len(short)
    if n == 0:
        return jaccard
    window = max(3, min(8, n // 2))
    hits = 0
    total = 0
    for i in range(0, n - window + 1):
        chunk = short[i : i + window]
        total += 1
        if chunk in long_:
            hits += 1
    char_cov = hits / total if total else 0.0

    return 0.5 * jaccard + 0.5 * char_cov


def _tokens(s: str) -> list[str]:
    out: list[str] = []
    cur: list[str] = []
    for ch in s.lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return out
