"""Application settings.

Single source of truth for every tunable. Read once at startup; never
mutated. Backed by env vars (see /.env.example) and validated by pydantic.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    _HERE = Path(__file__).resolve()
    _BACKEND_DIR = _HERE.parents[1]  # .../backend
    _REPO_ROOT = _HERE.parents[2]  # .../crpf

    model_config = SettingsConfigDict(
        env_prefix="PRAMAAN_",
        # Use absolute paths so starting uvicorn from different working
        # directories still picks up the intended .env.
        env_file=(
            str(_BACKEND_DIR / ".env"),
            str(_REPO_ROOT / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ─── Application ──────────────────────────────────────────────────────
    env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_origin: str = "http://localhost:3000"

    # ─── Postgres ─────────────────────────────────────────────────────────
    db_url: str = "postgresql+psycopg://pramaan:pramaan@localhost:5433/pramaan"

    # ─── S3 / MinIO ───────────────────────────────────────────────────────
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "pramaan"
    s3_secret_key: str = "pramaanpramaan"
    s3_bucket: str = "pramaan"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    # ─── Qdrant ───────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"

    # ─── OPA ──────────────────────────────────────────────────────────────
    opa_url: str = "http://localhost:8181"

    # ─── LLM (OpenAI-compatible: Groq, OpenRouter, OpenAI, Ollama, …) ─────
    llm_provider: str = "groq"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_extractor_model: str = "llama-3.1-70b-versatile"
    llm_skeptic_model: str = "llama-3.1-70b-versatile"
    llm_vlm_model: str = "llama-3.1-70b-versatile"
    llm_temperature: float = 0.0
    llm_seed: int = 42
    llm_max_tokens: int = 4096
    llm_timeout_s: int = 60
    llm_mock: bool = False
    """If True, never calls an upstream LLM (uses deterministic stubs)."""

    llm_send_seed: bool = False
    """Groq and several gateways ignore or reject `seed`; set False unless your provider supports it."""

    openrouter_http_referer: str = ""
    """Optional `HTTP-Referer` for OpenRouter (`HTTP-Referer` analytics header); defaults to `frontend_origin`."""

    # ─── OCR ──────────────────────────────────────────────────────────────
    tesseract_path: str = ""
    use_paddleocr: bool = False

    # ─── Audit ledger ─────────────────────────────────────────────────────
    signing_key_path: str = "./storage/keys/signing_key.pem"
    signing_key_id: str = "pramaan-dev-2026"

    # ─── Auth (mock OIDC for dev) ─────────────────────────────────────────
    auth_mode: Literal["mock", "oidc"] = "mock"
    mock_officer_id: str = "officer:abc@crpf.gov.in"
    mock_officer_name: str = "Inspector A. B. Singh"

    # ─── Local storage paths ──────────────────────────────────────────────
    storage_root: Path = Field(default_factory=lambda: Path("./storage").resolve())

    # ─── Confidence thresholds (Adjudicator + Excavator) ──────────────────
    confidence_t1: float = 0.80  # individual node minimum
    confidence_t2: float = 0.90  # cross-document agreement minimum

    @property
    def is_mock_llm(self) -> bool:
        """True when mock forced, key missing, or key still looks like a template."""
        if self.llm_mock:
            return True

        key = self.llm_api_key.strip()

        if not key:
            return True
        # `.env.example` ships `sk-or-v1-REPLACE_ME` — non-empty but unusable; don't hammer the provider with 401s.
        k = key.lower()
        placeholders = (
            "replace_me",
            "replace-me",
            "changeme",
            "paste_your",
            "your_key_here",
            "your-api-key",
            "insert_api_key",
        )
        if any(p in k for p in placeholders):
            return True
        return False



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
