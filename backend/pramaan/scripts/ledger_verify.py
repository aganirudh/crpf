"""Verify the audit ledger hash chain.

Usage:
  python -m pramaan.scripts.ledger_verify
  python -m pramaan.scripts.ledger_verify --tender <uuid>
"""

from __future__ import annotations

import argparse
import uuid

from rich.console import Console

from pramaan.db.session import session_scope
from pramaan.ledger.chain import Ledger

console = Console()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tender", type=str, default=None, help="restrict to one tender UUID")
    args = parser.parse_args()

    tid = uuid.UUID(args.tender) if args.tender else None
    with session_scope() as db:
        ledger = Ledger(db)
        ok, n, last = ledger.verify(tender_id=tid)

    if ok:
        console.print(
            f"[bold green]Verifying {n} events...  OK[/bold green] "
            f"(chain intact, last hash sha256:{last[:32]}…)"
        )
        return 0
    console.print(f"[bold red]CHAIN BROKEN[/bold red] after {n} events; last good hash {last[:32]}…")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
