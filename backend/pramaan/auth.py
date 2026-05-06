"""Auth — mock OIDC for dev, real OIDC for prod.

`get_current_officer` is a FastAPI dependency that resolves the calling
officer to an `Officer` row (creating it lazily on first sight in dev).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from pramaan.config import settings
from pramaan.db.models import Officer
from pramaan.db.session import get_db


@dataclass(frozen=True)
class CurrentOfficer:
    id: str  # internal UUID as string
    external_id: str
    name: str
    role: str


def get_current_officer(db: Session = Depends(get_db)) -> CurrentOfficer:
    if settings.auth_mode == "mock":
        return _ensure_mock_officer(db)
    raise NotImplementedError("OIDC mode pending — add an OIDC issuer config and JWT verification.")


def _ensure_mock_officer(db: Session) -> CurrentOfficer:
    stmt = select(Officer).where(Officer.external_id == settings.mock_officer_id)
    officer = db.execute(stmt).scalar_one_or_none()
    if officer is None:
        officer = Officer(
            external_id=settings.mock_officer_id,
            name=settings.mock_officer_name,
            role="evaluator-signer",
        )
        db.add(officer)
        db.commit()
        db.refresh(officer)
    return CurrentOfficer(
        id=str(officer.id),
        external_id=officer.external_id,
        name=officer.name,
        role=officer.role,
    )
