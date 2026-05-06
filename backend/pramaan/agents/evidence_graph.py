"""Evidence Graph view — per-bidder aggregation across documents.

The Excavator persists raw `EvidenceNode` rows. Many fields naturally
appear in multiple documents (turnover in both audited FS and CA cert;
GSTIN on a GST RC and a letterhead). The Adjudicator wants a single
canonical answer per `(field, fy)` plus a confidence score that
*combines* the individual node confidences with cross-document agreement.

Contract:
  * `build_evidence_graph(session, bidder_id)` returns an
    `EvidenceGraphView` — a list of `FieldAggregate` rows.
  * Each `FieldAggregate` carries:
      - the canonical (normalised) value
      - the FY (or None for un-scoped fields)
      - all contributing nodes (with per-source values + bboxes)
      - `agreement_score`: how strongly the sources agree
      - `final_conf`: min over contributing nodes' final_conf,
        further depressed if `agreement_score < 0.9` (cross-doc disagreement)
  * Disagreements (`agreement_score < 0.9` AND >= 2 sources) raise
    `cross_doc_disagreement = True`. The Adjudicator routes those to
    Manual Review (W4); the Officer UX (W5) shows both side-by-side.

This module is pure: no LLM calls, no I/O outside the DB read.
"""

from __future__ import annotations

import statistics
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from pramaan.db.models import EvidenceNode

# ─── Types ────────────────────────────────────────────────────────────────


@dataclass
class FieldSource:
    """One contributing extraction node."""

    node_id: uuid.UUID
    document_id: uuid.UUID
    value: Any
    page: int
    bbox: tuple[float, float, float, float]
    final_conf: float
    extractor_conf: float
    ocr_conf: float
    provenance_match_conf: float
    source_quote: str | None


@dataclass
class FieldAggregate:
    """One canonical answer for a `(field, fy)` pair."""

    field: str
    fy: str | None
    value: Any
    """Canonical value (the modal value across sources, or the highest-conf
    one if all sources disagree). Numeric fields use the median when sources
    are within tolerance, otherwise expose the disagreement and pick max."""

    sources: list[FieldSource] = field(default_factory=list)
    agreement_score: float = 1.0
    final_conf: float = 0.0
    cross_doc_disagreement: bool = False

    @property
    def n_sources(self) -> int:
        return len(self.sources)


@dataclass
class EvidenceGraphView:
    bidder_id: uuid.UUID
    fields: list[FieldAggregate] = field(default_factory=list)

    def by_field(self, name: str, fy: str | None = None) -> list[FieldAggregate]:
        return [a for a in self.fields if a.field == name and (fy is None or a.fy == fy)]


# ─── Builder ──────────────────────────────────────────────────────────────


# Numeric tolerance for "agreement" between two values of the same field.
# 5% matches the common cross-check in the brief (turnover across
# audited FS vs CA cert).
_NUMERIC_TOLERANCE_PCT = 5.0


def build_evidence_graph(session: Session, bidder_id: uuid.UUID) -> EvidenceGraphView:
    rows = session.execute(
        select(EvidenceNode).where(EvidenceNode.bidder_id == bidder_id)
    ).scalars().all()

    # Group by (field, fy).
    buckets: dict[tuple[str, str | None], list[EvidenceNode]] = {}
    for node in rows:
        key = (node.field, node.fy)
        buckets.setdefault(key, []).append(node)

    out: list[FieldAggregate] = []
    for (field_name, fy), nodes in buckets.items():
        agg = _aggregate(field_name=field_name, fy=fy, nodes=nodes)
        out.append(agg)

    # Stable order: field asc, then fy asc (None first).
    out.sort(key=lambda a: (a.field, a.fy or ""))
    return EvidenceGraphView(bidder_id=bidder_id, fields=out)


# ─── Internals ────────────────────────────────────────────────────────────


def _aggregate(*, field_name: str, fy: str | None, nodes: list[EvidenceNode]) -> FieldAggregate:
    sources = [_to_source(n) for n in nodes]
    values = [s.value for s in sources]

    if all(_is_numeric(v) for v in values):
        canonical, agreement = _aggregate_numeric([float(v) for v in values])
    elif all(isinstance(v, bool) for v in values):
        canonical, agreement = _aggregate_categorical([bool(v) for v in values])
    else:
        canonical, agreement = _aggregate_categorical(values)

    base_conf = min(s.final_conf for s in sources) if sources else 0.0
    # Penalise disagreement: scale conf down to (agreement) of itself when
    # agreement is low. Saturated agreement (= 1.0) leaves conf untouched.
    final_conf = base_conf * (0.5 + 0.5 * agreement)

    cross_doc_disagreement = (
        len({s.document_id for s in sources}) >= 2 and agreement < 0.9
    )

    return FieldAggregate(
        field=field_name,
        fy=fy,
        value=canonical,
        sources=sources,
        agreement_score=round(agreement, 4),
        final_conf=round(max(0.0, min(1.0, final_conf)), 4),
        cross_doc_disagreement=cross_doc_disagreement,
    )


def _to_source(n: EvidenceNode) -> FieldSource:
    bbox = tuple(n.bbox) if isinstance(n.bbox, list) else n.bbox  # type: ignore[assignment]
    return FieldSource(
        node_id=n.id,
        document_id=n.document_id,
        value=n.value,
        page=n.page,
        bbox=bbox,  # type: ignore[arg-type]
        final_conf=float(n.final_conf),
        extractor_conf=float(n.extractor_conf or 0.0),
        ocr_conf=float(n.ocr_conf or 0.0),
        provenance_match_conf=float(n.provenance_match_conf or 0.0),
        source_quote=n.source_quote,
    )


def _is_numeric(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _aggregate_numeric(values: list[float]) -> tuple[float, float]:
    """Return (canonical, agreement_score in [0,1])."""
    if not values:
        return 0.0, 1.0
    if len(values) == 1:
        v = values[0]
        return (int(v) if v.is_integer() else v), 1.0

    canonical = statistics.median(values)
    if canonical == 0:
        agreement = 1.0 if all(v == 0 for v in values) else 0.0
    else:
        max_dev = max(abs((v - canonical) / canonical) for v in values)
        max_dev_pct = max_dev * 100.0
        if max_dev_pct <= _NUMERIC_TOLERANCE_PCT:
            agreement = 1.0
        elif max_dev_pct >= 50.0:
            agreement = 0.0
        else:
            # Linear ramp between tolerance and 50%.
            span = 50.0 - _NUMERIC_TOLERANCE_PCT
            agreement = max(0.0, 1.0 - (max_dev_pct - _NUMERIC_TOLERANCE_PCT) / span)

    coerced = (
        int(canonical) if isinstance(canonical, float) and canonical.is_integer() else canonical
    )
    return coerced, round(agreement, 4)


def _aggregate_categorical(values: list) -> tuple[Any, float]:
    if not values:
        return None, 1.0

    # Count occurrences via stringified-canonical hashable key.
    counts: dict[str, list[Any]] = {}
    for v in values:
        k = _hash_key(v)
        counts.setdefault(k, []).append(v)

    if len(counts) == 1:
        return values[0], 1.0

    # Modal value wins; agreement is its share of the population.
    best_key = max(counts.keys(), key=lambda k: len(counts[k]))
    best_value = counts[best_key][0]
    agreement = len(counts[best_key]) / len(values)
    return best_value, round(agreement, 4)


def _hash_key(v: Any) -> str:
    if isinstance(v, str):
        return v.strip().lower()
    return repr(v)
