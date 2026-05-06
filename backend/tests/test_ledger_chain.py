"""Hash-chain integrity tests using an in-memory SQLite stand-in.

These exercise the `Ledger` logic without needing Postgres up.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker

from pramaan.db.base import Base
from pramaan.db.models import LedgerEvent  # noqa: F401  -- ensure model is imported
from pramaan.ledger.chain import Ledger


def _sqlite_engine():
    # SQLite doesn't have JSONB or BIGSERIAL or gen_random_uuid(); we adapt.
    eng = sa.create_engine("sqlite:///:memory:", future=True)
    # Replace JSONB with JSON for SQLite, server defaults removed.
    for table in Base.metadata.sorted_tables:
        for col in table.columns:
            if isinstance(col.type, postgresql.JSONB):
                col.type = sa.JSON()
            if col.server_default is not None:
                col.server_default = None
            if col.name == "seq":
                col.autoincrement = True
    Base.metadata.create_all(eng)
    return eng


def test_ledger_chain_is_intact_after_appends():
    engine = _sqlite_engine()
    SessionLocal = sessionmaker(bind=engine, future=True)
    with SessionLocal.begin() as db:
        ledger = Ledger(db)
        ledger.append(kind="tender.uploaded", actor="officer:a", payload={"x": 1})
        ledger.append(kind="dsl.confirmed", actor="officer:a", payload={"y": 2})
        ledger.append(kind="verdict.final", actor="adjudicator", payload={"z": [1, 2, 3]})

    with SessionLocal.begin() as db:
        ok, n, last = Ledger(db).verify()
        assert ok
        assert n == 3
        assert len(last) == 64
