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
    model_config = SettingsConfigDict(
        env_prefix="PRAMAAN_",
        env_file=(".env", "../.env"),
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
    db_url: str = "postgresql+psycopg://pramaan:pramaan@localhost:5432/pramaan"

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

    # ─── LLM ──────────────────────────────────────────────────────────────
    llm_provider: str = "openrouter"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_extractor_model: str = "meta-llama/llama-3.1-70b-instruct"
    llm_skeptic_model: str = "qwen/qwen-2.5-72b-instruct"
    llm_vlm_model: str = "qwen/qwen-2.5-vl-72b-instruct"
    llm_temperature: float = 0.0
    llm_seed: int = 42
    llm_max_tokens: int = 4096
    llm_timeout_s: int = 120
    llm_mock: bool = False

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
        """True when no API key was provided OR mock mode forced."""
        return self.llm_mock or not self.llm_api_key.strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
