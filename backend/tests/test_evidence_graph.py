"""Unit tests for per-bidder evidence graph aggregation (W3).

Uses lightweight stand-ins for ORM rows — only the attributes read by
`build_evidence_graph` / `_to_source` are required.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from pramaan.agents.evidence_graph import build_evidence_graph


def _node(
    *,
    bidder_id: uuid.UUID,
    document_id: uuid.UUID,
    field: str,
    fy: str | None,
    value,
    page: int = 1,
    bbox: list[float] | None = None,
    final_conf: float = 0.95,
    extractor_conf: float = 0.95,
    ocr_conf: float = 0.92,
    provenance_match_conf: float = 0.96,
    source_quote: str | None = "quote",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        bidder_id=bidder_id,
        document_id=document_id,
        field=field,
        fy=fy,
        value=value,
        page=page,
        bbox=bbox or [0.0, 0.0, 100.0, 40.0],
        final_conf=final_conf,
        extractor_conf=extractor_conf,
        ocr_conf=ocr_conf,
        provenance_match_conf=provenance_match_conf,
        source_quote=source_quote,
    )


def _mock_session(rows: list[SimpleNamespace]):
    """Minimal stub: `execute(select(...)).scalars().all()` → rows."""
    scalars = SimpleNamespace(all=lambda: rows)
    result = SimpleNamespace(scalars=lambda: scalars)

    def execute(_stmt):  # noqa: ANN001
        return result

    return SimpleNamespace(execute=execute)  # type: ignore[return-value]


def test_single_numeric_field_full_agreement():
    bidder = uuid.uuid4()
    doc = uuid.uuid4()
    rows = [_node(bidder_id=bidder, document_id=doc, field="turnover_inr", fy="FY23", value=1_000_000)]
    view = build_evidence_graph(_mock_session(rows), bidder)
    assert len(view.fields) == 1
    agg = view.fields[0]
    assert agg.field == "turnover_inr"
    assert agg.fy == "FY23"
    assert agg.value == 1_000_000
    assert agg.agreement_score == 1.0
    assert agg.cross_doc_disagreement is False
    assert agg.n_sources == 1


def test_two_documents_numeric_within_tolerance():
    bidder = uuid.UUID(int=1)
    d1, d2 = uuid.UUID(int=2), uuid.UUID(int=3)
    # 100 vs 103 → 3% deviation from median ~101.5 ... actually median is 101.5, max dev from median?
    # values 1000000 and 1020000 → median 1010000, max abs dev / median = 20000/1010000 ≈ 1.98% → agreement 1.0
    rows = [
        _node(bidder_id=bidder, document_id=d1, field="revenue", fy=None, value=1_000_000),
        _node(bidder_id=bidder, document_id=d2, field="revenue", fy=None, value=1_020_000),
    ]
    view = build_evidence_graph(_mock_session(rows), bidder)
    agg = view.fields[0]
    assert agg.cross_doc_disagreement is False
    assert agg.agreement_score == 1.0
    assert agg.n_sources == 2


def test_cross_document_disagreement_numeric():
    bidder = uuid.UUID(int=10)
    d1, d2 = uuid.UUID(int=11), uuid.UUID(int=12)
    rows = [
        _node(bidder_id=bidder, document_id=d1, field="revenue", fy=None, value=100),
        _node(bidder_id=bidder, document_id=d2, field="revenue", fy=None, value=200),
    ]
    view = build_evidence_graph(_mock_session(rows), bidder)
    agg = view.fields[0]
    assert agg.n_sources == 2
    assert agg.cross_doc_disagreement is True
    assert agg.agreement_score < 0.9


def test_categorical_agreement_two_docs():
    bidder = uuid.UUID(int=20)
    d1, d2 = uuid.UUID(int=21), uuid.UUID(int=22)
    gst = "22AAAAA0000A1Z5"
    rows = [
        _node(bidder_id=bidder, document_id=d1, field="gstin", fy=None, value=gst),
        _node(bidder_id=bidder, document_id=d2, field="gstin", fy=None, value=gst.lower()),
    ]
    view = build_evidence_graph(_mock_session(rows), bidder)
    agg = view.fields[0]
    assert agg.agreement_score == 1.0
    assert agg.cross_doc_disagreement is False


def test_separate_fy_buckets():
    bidder = uuid.UUID(int=30)
    doc = uuid.UUID(int=31)
    rows = [
        _node(bidder_id=bidder, document_id=doc, field="turnover_inr", fy="FY22", value=50),
        _node(bidder_id=bidder, document_id=doc, field="turnover_inr", fy="FY23", value=60),
    ]
    view = build_evidence_graph(_mock_session(rows), bidder)
    assert len(view.fields) == 2
    fys = {f.fy for f in view.fields}
    assert fys == {"FY22", "FY23"}
