"""Hash-chained audit ledger.

Every state change in PRAMAAN appends a `LedgerEvent` whose hash includes
the previous event's hash. Tampering with any past event invalidates the
chain from that point forward and is detectable in O(n).

Hashing rule (must stay byte-stable across language runtimes):

    payload_bytes = canonical_json(payload).encode("utf-8")
    event_hash    = sha256(payload_bytes || prev_hash || header_bytes)

where `header_bytes` deterministically encodes (kind, actor, ts iso) so the
hash also commits to the event metadata.

Canonical JSON follows RFC 8785 JCS to the extent we need: sorted keys,
no whitespace, UTF-8, escape only what JSON requires.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from pramaan.db.models import LedgerEvent

GENESIS = b"\x00" * 32


def canonical_json(value: Any) -> str:
    """Stable serialization for hashing.

    Sorted keys, no whitespace, ensures interop across languages. UUIDs and
    datetimes are stringified deterministically before serialization.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, datetime):
        # SQLite round-trips datetimes as naive; treat naive as UTC to keep
        # ledger hashes stable across backends.
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=UTC)
        return obj.astimezone(UTC).isoformat(timespec="microseconds")
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError(f"Cannot serialize {type(obj).__name__}")


def _header_bytes(*, kind: str, actor: str, ts: datetime) -> bytes:
    header = {"kind": kind, "actor": actor, "ts": _json_default(ts)}
    return canonical_json(header).encode("utf-8")


class Ledger:
    """Append events; verify the chain."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def latest_hash(self, *, tender_id: uuid.UUID | None = None) -> bytes:
        """Return the hash of the most recent event (globally, or per-tender).

        Per-tender hashing scopes a 'mini-chain' for each tender so a single
        signed report can carry a clean tender-scoped root hash.
        """
        stmt = select(LedgerEvent.hash).order_by(LedgerEvent.seq.desc()).limit(1)
        if tender_id is not None:
            stmt = (
                select(LedgerEvent.hash)
                .where(LedgerEvent.tender_id == tender_id)
                .order_by(LedgerEvent.seq.desc())
                .limit(1)
            )
        row = self.session.execute(stmt).scalar_one_or_none()
        return row or GENESIS

    def append(
        self,
        *,
        kind: str,
        actor: str,
        payload: dict[str, Any],
        tender_id: uuid.UUID | None = None,
        bidder_id: uuid.UUID | None = None,
    ) -> LedgerEvent:
        ts = datetime.now(UTC)
        prev = self.latest_hash(tender_id=tender_id)
        payload_bytes = canonical_json(payload).encode("utf-8")
        h = hashlib.sha256()
        h.update(payload_bytes)
        h.update(prev)
        h.update(_header_bytes(kind=kind, actor=actor, ts=ts))
        event_hash = h.digest()

        event = LedgerEvent(
            ts=ts,
            actor=actor,
            kind=kind,
            tender_id=tender_id,
            bidder_id=bidder_id,
            payload=payload,
            prev_hash=prev if prev != GENESIS else None,
            hash=event_hash,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def verify(self, *, tender_id: uuid.UUID | None = None) -> tuple[bool, int, str]:
        """Re-hash the chain and confirm integrity. O(n) in events.

        Returns (ok, n_events, last_hash_hex).
        """
        stmt = select(LedgerEvent).order_by(LedgerEvent.seq.asc())
        if tender_id is not None:
            stmt = (
                select(LedgerEvent)
                .where(LedgerEvent.tender_id == tender_id)
                .order_by(LedgerEvent.seq.asc())
            )
        events = list(self.session.execute(stmt).scalars())
        prev = GENESIS
        for ev in events:
            payload_bytes = canonical_json(ev.payload).encode("utf-8")
            h = hashlib.sha256()
            h.update(payload_bytes)
            h.update(prev)
            h.update(_header_bytes(kind=ev.kind, actor=ev.actor, ts=ev.ts))
            recomputed = h.digest()
            if recomputed != ev.hash:
                return (False, len(events), prev.hex())
            prev = ev.hash
        return (True, len(events), prev.hex())


def get_ledger(session: Session) -> Ledger:
    return Ledger(session)
