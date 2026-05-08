"""/healthz, /readyz, /info — operational endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from pramaan import __version__
from pramaan.config import settings
from pramaan.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@router.get("/info")
def info() -> dict[str, object]:
    key = (settings.llm_api_key or "").strip()
    model = settings.llm_extractor_model

    return {
        "name": "PRAMAAN",
        "version": __version__,
        "env": settings.env,
        "llm_provider": settings.llm_provider,
        "llm_extractor_model": model,
        "mock_llm": settings.is_mock_llm,
        "llm_mock_flag": settings.llm_mock,
        "llm_api_key_set": bool(key),
        "llm_api_key_prefix": (key[:6] + "…" if key else None),
        "auth_mode": settings.auth_mode,
    }

