"""Seed the brief's sample tender + 10 mock bidders for the demo.

Idempotent. Re-running picks up where the last run left off (matched by
SHA-256 of the input documents).

Run:
    make seed
"""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console

console = Console()


SAMPLES_ROOT = Path(__file__).resolve().parents[3] / "samples" / "tender_construction_2026"


def main() -> int:
    if not SAMPLES_ROOT.exists():
        console.print(f"[yellow]Samples folder not found: {SAMPLES_ROOT}[/yellow]")
        console.print("Add a tender PDF and bidder folders, then re-run `make seed`.")
        return 1

    console.print(f"[bold]Seeding from {SAMPLES_ROOT}[/bold]")
    console.print("[dim]Note: full implementation lands with the Excavator (W3).[/dim]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
