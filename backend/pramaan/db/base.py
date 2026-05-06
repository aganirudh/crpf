"""SQLAlchemy declarative base + shared mixins.

We use SQLAlchemy 2.x typed `Mapped` style throughout. JSONB-heavy schema:
the EvidenceGraph and CriterionDSL live in JSONB columns so the schema can
evolve without migrations as the DSL grammar grows.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Project-wide declarative base."""


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    """Adds created_at / updated_at, server-side defaulted."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPKMixin:
    """UUID primary key, generated DB-side via gen_random_uuid()."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
