"""Drop + recreate + migrate. Dev only.

Refuses to run if PRAMAAN_ENV != 'dev' to prevent shooting yourself in the
foot in production.
"""

from __future__ import annotations

import subprocess
import sys

from sqlalchemy import text

from pramaan.config import settings
from pramaan.db.base import Base
from pramaan.db.session import engine


def main() -> int:
    if settings.env != "dev":
        print(f"refusing to db-reset: PRAMAAN_ENV={settings.env!r}")
        return 1

    print("dropping all tables...")
    with engine.begin() as conn:
        Base.metadata.drop_all(conn)
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        print("recreating tables from models...")
        Base.metadata.create_all(conn)

    print("DB reset complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
