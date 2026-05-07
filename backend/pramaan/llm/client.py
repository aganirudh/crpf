"""LLM client — OpenAI-compatible, with structured-output enforcement and
deterministic mock fallback.

Why this is its own module:
  * Every LLM call must record `(model, prompt_hash, params)` so the audit
    ledger can reproduce evaluations later. We centralise that bookkeeping.
  * Provider swap (OpenAI → Groq → Ollama → Colab-vLLM) is one env-var change.
  * Mock mode lets us run tests / develop offline without surprises.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, TypeVar

import instructor
from openai import OpenAI
from pydantic import BaseModel

from pramaan.config import settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# ─── Hashing ───────────────────────────────────────────────────────────────


def prompt_hash(template: str, **fingerprint_fields: Any) -> str:
    """Stable hash of a prompt template + its versioned fingerprint.

    `fingerprint_fields` lets callers add things like template version, model
    family, etc. into the hash so future template edits invalidate cached
    results.
    """
    h = hashlib.sha256()
    h.update(template.encode("utf-8"))
    for key in sorted(fingerprint_fields):
        h.update(b"\x1e")
        h.update(key.encode("utf-8"))
        h.update(b"=")
        h.update(json.dumps(fingerprint_fields[key], sort_keys=True, default=str).encode("utf-8"))
    return h.hexdigest()


# ─── Result wrapper ────────────────────────────────────────────────────────


@dataclass
class LLMResult[T: BaseModel]:
    """A typed structured-output response plus the audit metadata that
    accompanied its production."""

    value: T
    model: str
    prompt_hash: str
    raw_response: dict[str, Any] | None = None


# ─── Client ────────────────────────────────────────────────────────────────


class LLMClient:
    """Thin wrapper over the OpenAI-compatible SDK + Instructor.

    * `extract(...)` enforces structured output against a pydantic model.
    * `chat(...)` returns a free-form string; reserved for the Skeptic agent
      where we want narrative prose.
    """

    def __init__(self) -> None:
        self.mock = settings.is_mock_llm
        if self.mock:
            log.info(
                "LLM client in MOCK mode — using deterministic stubs "
                "(empty/template API key or PRAMAAN_LLM_MOCK=1)."
            )
            self._client: OpenAI | None = None
            self._instructor: Any | None = None
        else:
            client_kw: dict[str, Any] = {
                "base_url": settings.llm_base_url,
                "api_key": settings.llm_api_key,
            }
            # OpenRouter recommends these headers for rankings / fewer odd failures with some SDK paths.
            if "openrouter.ai" in settings.llm_base_url.lower():
                referer = settings.openrouter_http_referer.strip() or settings.frontend_origin
                client_kw["default_headers"] = {
                    "HTTP-Referer": referer,
                    "X-Title": "PRAMAAN",
                }
            base = OpenAI(**client_kw)
            self._client = base
            self._instructor = instructor.from_openai(base, mode=instructor.Mode.JSON)

    # ── public ────────────────────────────────────────────────────────────

    def extract[T: BaseModel](
        self,
        *,
        response_model: type[T],
        system: str,
        user: str,
        model: str | None = None,
        prompt_template_version: str = "v1",
        max_retries: int = 2,
    ) -> LLMResult[T]:
        """Structured-output extraction.

        On mock, dispatches to `pramaan.llm.mock.fake_extract` so callers
        get a deterministic value of the right type.
        """
        chosen_model = model or settings.llm_extractor_model
        ph = prompt_hash(
            system + "\n\n---\n\n" + user,
            model=chosen_model,
            schema=response_model.__name__,
            template_version=prompt_template_version,
            temperature=settings.llm_temperature,
            seed=settings.llm_seed,
        )

        if self.mock:
            from pramaan.llm.mock import fake_extract

            value = fake_extract(response_model, system=system, user=user)
            return LLMResult(value=value, model=f"mock://{chosen_model}", prompt_hash=ph)

        assert self._instructor is not None
        t0 = time.perf_counter()
        kwargs: dict[str, Any] = {
            "model": chosen_model,
            "response_model": response_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "timeout": settings.llm_timeout_s,
            "max_retries": max_retries,
        }
        if settings.llm_send_seed:
            kwargs["seed"] = settings.llm_seed
        try:
            log.info(
                "llm.extract start (provider=%s base_url=%s model=%s schema=%s timeout_s=%s)",
                settings.llm_provider,
                settings.llm_base_url,
                chosen_model,
                response_model.__name__,
                settings.llm_timeout_s,
            )
            value = self._instructor.chat.completions.create(**kwargs)
            dt = time.perf_counter() - t0
            log.info(
                "llm.extract ok (model=%s schema=%s prompt_hash=%s elapsed_s=%.2f)",
                chosen_model,
                response_model.__name__,
                ph[:12],
                dt,
            )
            return LLMResult(value=value, model=chosen_model, prompt_hash=ph)
        except Exception as exc:
            dt = time.perf_counter() - t0
            exc_str = str(exc)
            # Surface auth errors clearly instead of burying in retry XML
            if "401" in exc_str or "Unauthorized" in exc_str or "User not found" in exc_str:
                log.error(
                    "LLM API KEY IS INVALID (401 Unauthorized). "
                    "Provider: %s, Base URL: %s. "
                    "Please update PRAMAAN_LLM_API_KEY in your .env file with a valid key.",
                    settings.llm_provider,
                    settings.llm_base_url,
                )
                raise RuntimeError(
                    f"LLM API key is invalid or expired (401 Unauthorized from {settings.llm_provider}). "
                    f"Please get a new API key from your provider and update PRAMAAN_LLM_API_KEY in .env, "
                    f"then restart the backend."
                ) from exc
            log.exception(
                "llm.extract failed (provider=%s base_url=%s model=%s schema=%s elapsed_s=%.2f prompt_hash=%s)",
                settings.llm_provider,
                settings.llm_base_url,
                chosen_model,
                response_model.__name__,
                dt,
                ph[:12],
            )
            raise

    def chat(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        prompt_template_version: str = "v1",
    ) -> LLMResult[_StringWrap]:
        """Free-form chat. Returns the model's text wrapped for uniformity."""
        chosen_model = model or settings.llm_skeptic_model
        ph = prompt_hash(
            system + "\n\n---\n\n" + user,
            model=chosen_model,
            template_version=prompt_template_version,
            temperature=settings.llm_temperature,
            seed=settings.llm_seed,
        )
        if self.mock:
            from pramaan.llm.mock import fake_chat

            text = fake_chat(system=system, user=user)
            return LLMResult(
                value=_StringWrap(text=text),
                model=f"mock://{chosen_model}",
                prompt_hash=ph,
            )

        assert self._client is not None
        kwargs: dict[str, Any] = {
            "model": chosen_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "timeout": settings.llm_timeout_s,
        }
        if settings.llm_send_seed:
            kwargs["seed"] = settings.llm_seed
        rsp = self._client.chat.completions.create(**kwargs)
        text = rsp.choices[0].message.content or ""
        return LLMResult(
            value=_StringWrap(text=text),
            model=chosen_model,
            prompt_hash=ph,
            raw_response=rsp.model_dump(),
        )

    def vision(
        self,
        *,
        response_model: type[T],
        system: str,
        user: str,
        image_b64s: Sequence[str],
        model: str | None = None,
        prompt_template_version: str = "v1",
    ) -> LLMResult[T]:
        """VLM call (Qwen2.5-VL etc.) for stamps/photos.

        Images are passed inline via the OpenAI vision content schema.
        """
        chosen_model = model or settings.llm_vlm_model
        ph = prompt_hash(
            system + "\n\n---\n\n" + user,
            model=chosen_model,
            schema=response_model.__name__,
            template_version=prompt_template_version,
            n_images=len(image_b64s),
        )

        if self.mock:
            from pramaan.llm.mock import fake_extract

            value = fake_extract(response_model, system=system, user=user)
            return LLMResult(value=value, model=f"mock://{chosen_model}", prompt_hash=ph)

        assert self._instructor is not None
        content: list[dict[str, Any]] = [{"type": "text", "text": user}]
        for b64 in image_b64s:
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
            )
        kwargs: dict[str, Any] = {
            "model": chosen_model,
            "response_model": response_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "timeout": settings.llm_timeout_s,
        }
        if settings.llm_send_seed:
            kwargs["seed"] = settings.llm_seed
        value = self._instructor.chat.completions.create(**kwargs)
        return LLMResult(value=value, model=chosen_model, prompt_hash=ph)


class _StringWrap(BaseModel):
    text: str


@lru_cache(maxsize=1)
def get_llm_client() -> Any:
    # Use GeminiClient by default as per Phase 4 requirements
    from pramaan.llm.gemini_client import GeminiClient
    return GeminiClient()
