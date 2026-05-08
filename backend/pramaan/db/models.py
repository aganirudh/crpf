"""ORM models — the tables that hold tenders, bidders, evidence, verdicts,
overrides, and the audit ledger.

Schema follows `docs/02-architecture.md` § 4.1.

Design notes:
  * UUID primary keys everywhere (issued by Postgres `gen_random_uuid()`).
  * Heavy-shape data (CriterionDSL, EvidenceGraph values) lives in JSONB so
    the schema can evolve without migrations as the DSL grammar grows.
  * `LedgerEvent` is intentionally append-only: there is no `updated_at`,
    no foreign keys *out of* the row that could be CASCADE-deleted, and the
    application role's grants will revoke UPDATE/DELETE in production.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pramaan.db.base import Base, TimestampMixin, UUIDPKMixin


# ─── Tenant / officer ─────────────────────────────────────────────────────


class Officer(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "officer"

    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="evaluator")


# ─── Tender ───────────────────────────────────────────────────────────────


class Tender(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "tender"

    reference_no: Mapped[str | None] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False, unique=True)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)
    classification: Mapped[str | None] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)

    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("officer.id"), nullable=False)
    uploaded_by: Mapped[Officer] = relationship()

    bidders: Mapped[list["Bidder"]] = relationship(back_populates="tender", cascade="all, delete-orphan")
    dsl: Mapped["CriterionDSLRow | None"] = relationship(
        back_populates="tender", uselist=False, cascade="all, delete-orphan"
    )


class CriterionDSLRow(Base, TimestampMixin):
    __tablename__ = "criterion_dsl"

    tender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tender.id", ondelete="CASCADE"), primary_key=True
    )
    dsl: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dsl_sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    dsl_version: Mapped[str] = mapped_column(String(16), nullable=False, default="v1")

    source_model: Mapped[str] = mapped_column(String(255), nullable=False)
    source_prompt_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    cartographer_run_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("officer.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tender: Mapped[Tender] = relationship(back_populates="dsl")


# ─── Bidder ───────────────────────────────────────────────────────────────


class Bidder(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "bidder"

    tender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tender.id", ondelete="CASCADE"), nullable=False
    )
    legal_name: Mapped[str | None] = mapped_column(String(512))
    cin: Mapped[str | None] = mapped_column(String(32))
    gstin: Mapped[str | None] = mapped_column(String(32))
    pan: Mapped[str | None] = mapped_column(String(16))
    bid_price_inr: Mapped[int | None] = mapped_column(BigInteger)
    selection_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")  # pending, accepted, rejected

    tender: Mapped[Tender] = relationship(back_populates="bidders")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="bidder", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_bidder_tender", "tender_id"),)


class Document(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "document"

    bidder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bidder.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)
    classification: Mapped[str | None] = mapped_column(String(64))  # typed_pdf | scanned_pdf | photo | docx | xlsx

    bidder: Mapped[Bidder] = relationship(back_populates="documents")
    evidence_nodes: Mapped[list["EvidenceNode"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_document_bidder", "bidder_id"),
        UniqueConstraint("bidder_id", "sha256", name="uq_document_bidder_sha"),
    )


# ─── Evidence Graph ───────────────────────────────────────────────────────


class EvidenceNode(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "evidence_node"

    bidder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bidder.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"), nullable=False
    )

    field: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32))
    fy: Mapped[str | None] = mapped_column(String(16))

    page: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox: Mapped[list[float]] = mapped_column(JSONB, nullable=False)  # [x0,y0,x1,y1]

    ocr_conf: Mapped[float | None] = mapped_column(Float)
    extractor_conf: Mapped[float | None] = mapped_column(Float)
    provenance_match_conf: Mapped[float | None] = mapped_column(Float)
    final_conf: Mapped[float] = mapped_column(Float, nullable=False)

    extractor_model: Mapped[str] = mapped_column(String(255), nullable=False)
    extractor_prompt_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    source_text_sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    source_quote: Mapped[str | None] = mapped_column(Text)

    document: Mapped[Document] = relationship(back_populates="evidence_nodes")

    __table_args__ = (
        Index("ix_evidence_bidder_field", "bidder_id", "field"),
        CheckConstraint("final_conf >= 0 AND final_conf <= 1", name="ck_final_conf_range"),
    )


# ─── Verdicts and overrides ───────────────────────────────────────────────


VERDICT_STATUSES = ("eligible", "not_eligible", "manual_review")


class Verdict(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "verdict"

    bidder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bidder.id", ondelete="CASCADE"), nullable=False
    )
    criterion_id: Mapped[str] = mapped_column(String(64), nullable=False)  # "C1" / "overall"
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason_tag: Mapped[str | None] = mapped_column(String(64))
    reason_text: Mapped[str | None] = mapped_column(Text)

    evidence_used: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    skeptic: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    validators: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    suggested_action: Mapped[str | None] = mapped_column(Text)

    rego_policy_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    opa_version: Mapped[str | None] = mapped_column(String(32))

    __table_args__ = (
        CheckConstraint(f"status IN {VERDICT_STATUSES}", name="ck_verdict_status"),
        Index("ix_verdict_bidder_criterion", "bidder_id", "criterion_id"),
    )


class Override(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "override"

    verdict_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verdict.id", ondelete="CASCADE"), nullable=False
    )
    officer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("officer.id"), nullable=False)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reason_tag: Mapped[str] = mapped_column(String(64), nullable=False)


# ─── Integrity findings ───────────────────────────────────────────────────


class IntegrityFlag(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "integrity_flag"

    tender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tender.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)  # cartel|capacity|forgery|statistical
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # info|warning|critical
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    suggested_action: Mapped[str | None] = mapped_column(Text)
    affected_bidder_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


# ─── Audit ledger (append-only, hash-chained) ─────────────────────────────


class LedgerEvent(Base):
    __tablename__ = "ledger_event"

    # NOTE: SQLite only auto-increments when the PK column is exactly INTEGER.
    # In Postgres we still want a BIGINT/BigSerial-like sequence.
    seq: Mapped[int] = mapped_column(
        Integer().with_variant(BigInteger, "postgresql"),
        primary_key=True,
        autoincrement=True,
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    tender_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tender.id"))
    bidder_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bidder.id"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    prev_hash: Mapped[bytes | None] = mapped_column(LargeBinary(32))
    hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False, unique=True)

    __table_args__ = (Index("ix_ledger_tender_seq", "tender_id", "seq"),)


# ─── Signed report bundles ────────────────────────────────────────────────


class ReportBundle(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "report_bundle"

    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tender.id"), nullable=False)
    bundle: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    bundle_sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False, unique=True)
    signature: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    signing_key_id: Mapped[str] = mapped_column(String(128), nullable=False)
    signed_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("officer.id"), nullable=False)
    ledger_root_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
