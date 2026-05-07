"""FastAPI entry point.

Wires routers, middleware, and lifespan startup. Keep this file boring;
all behavior lives in routers/services.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pramaan import __version__
from pramaan.config import settings
from pramaan.db.base import Base
from pramaan.db.session import engine
from pramaan.routers import bidders, health, tenders, auth

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("pramaan")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info(
        "PRAMAAN starting (env=%s, llm_provider=%s, mock_llm=%s)",
        settings.env,
        settings.llm_provider,
        settings.is_mock_llm,
    )
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    # Dev convenience: until Alembic revisions are committed, auto-create tables
    # so the MVP is runnable from a clean Postgres.
    if settings.env == "dev":
        from pramaan.db import models as _models  # noqa: F401

        Base.metadata.create_all(bind=engine)
    yield
    log.info("PRAMAAN shutting down")


app = FastAPI(
    title="PRAMAAN",
    description="AI tender evaluation for CRPF — sovereign, neuro-symbolic, auditable.",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(tenders.router, prefix="/api/v1")
app.include_router(bidders.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "PRAMAAN",
        "version": __version__,
        "tagline": "LLMs read. Symbolic logic decides. Cryptography proves. Humans approve.",
    }
