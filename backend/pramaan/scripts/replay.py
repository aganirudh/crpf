"""Replay a signed report bundle (W6).

Stub for now — implemented when the Scribe + signed-bundle work lands in W6.
The CLI exists already so the Makefile target works.
"""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()
    print(f"[replay] not yet implemented (target bundle: {args.bundle})")
    print("[replay] this CLI will re-execute the bundle's pinned artifacts and")
    print("         compare the resulting hash against the original. (W6)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
