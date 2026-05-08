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
import re
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

MAX_JSON_REPAIR_ATTEMPTS = 3


def _strip_json_fences(raw: str) -> str:
    """Remove common markdown code fences so `json.loads` can run."""
    text = (raw or "").strip()
    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"\s*```\s*$", "", text).strip()
    return text


def _parse_json_model(raw: str, response_model: type[T]) -> T:
    """Parse JSON text into a validated pydantic model."""
    text = _strip_json_fences(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Single-object tenders sometimes wrap extra prose — grab outermost {...}
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(text[start : end + 1])
        else:
            raise
    return response_model.model_validate(data)


def _map_llm_usage_error(exc: BaseException) -> RuntimeError | None:
    """Map common HTTP status patterns from OpenAI-compatible clients."""
    exc_str = str(exc)
    if "401" in exc_str or "Unauthorized" in exc_str or "User not found" in exc_str:
        log.error(
            "LLM API key rejected (401 Unauthorized). Endpoint: %s",
            settings.llm_base_url,
        )
        return RuntimeError(
            "LLM API key is invalid or expired (401 Unauthorized). "
            f"Endpoint: {settings.llm_base_url}. "
            "Set PRAMAAN_LLM_API_KEY to a valid key for that endpoint, then restart the backend."
        )
    if "402" in exc_str or "Payment Required" in exc_str or "insufficient_quota" in exc_str:
        log.error(
            "LLM provider quota or billing issue (402). Endpoint: %s",
            settings.llm_base_url,
        )
        return RuntimeError(
            f"LLM provider quota or billing limit (402) at {settings.llm_base_url}."
        )
    return None


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

        Live mode: tries Instructor JSON mode first, then falls back to a
        plain completion + JSON parse + pydantic validation with up to
        ``MAX_JSON_REPAIR_ATTEMPTS`` self-correction turns (Groq/Llama).
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

        assert self._client is not None and self._instructor is not None
        t0 = time.perf_counter()

        kwargs_base: dict[str, Any] = {
            "model": chosen_model,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "timeout": settings.llm_timeout_s,
        }
        if settings.llm_send_seed:
            kwargs_base["seed"] = settings.llm_seed

        log.info(
            "llm.extract start (provider=%s base_url=%s model=%s schema=%s timeout_s=%s)",
            settings.llm_provider,
            settings.llm_base_url,
            chosen_model,
            response_model.__name__,
            settings.llm_timeout_s,
        )

        try:
            kwargs_inst: dict[str, Any] = {
                **kwargs_base,
                "response_model": response_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_retries": max_retries,
            }
            value = self._instructor.chat.completions.create(**kwargs_inst)
            dt = time.perf_counter() - t0
            log.info(
                "llm.extract ok (model=%s schema=%s prompt_hash=%s elapsed_s=%.2f)",
                chosen_model,
                response_model.__name__,
                ph[:12],
                dt,
            )
            return LLMResult(value=value, model=chosen_model, prompt_hash=ph)
        except Exception as inst_exc:
            mapped = _map_llm_usage_error(inst_exc)
            if mapped is not None:
                raise mapped from inst_exc
            log.warning(
                "llm.extract instructor path failed (%s); trying JSON repair loop",
                inst_exc,
            )

        schema_snippet = json.dumps(
            response_model.model_json_schema(), indent=2, default=str
        )
        if len(schema_snippet) > 12000:
            schema_snippet = schema_snippet[:12000] + "\n... (truncated)"

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        last_raw = ""
        last_err: BaseException | None = None

        for repair_attempt in range(MAX_JSON_REPAIR_ATTEMPTS):
            try:
                rsp = self._client.chat.completions.create(
                    **kwargs_base,
                    messages=messages,
                )
                last_raw = rsp.choices[0].message.content or ""
                value = _parse_json_model(last_raw, response_model)
                dt = time.perf_counter() - t0
                log.info(
                    "llm.extract ok (repair path attempt=%s model=%s schema=%s prompt_hash=%s elapsed_s=%.2f)",
                    repair_attempt + 1,
                    chosen_model,
                    response_model.__name__,
                    ph[:12],
                    dt,
                )
                return LLMResult(value=value, model=chosen_model, prompt_hash=ph)
            except Exception as exc:
                last_err = exc
                mapped = _map_llm_usage_error(exc)
                if mapped is not None:
                    raise mapped from exc
                log.warning(
                    "llm.extract repair attempt %s/%s failed: %s",
                    repair_attempt + 1,
                    MAX_JSON_REPAIR_ATTEMPTS,
                    exc,
                )
                if repair_attempt >= MAX_JSON_REPAIR_ATTEMPTS - 1:
                    log.error(
                        "llm.extract repair exhausted; last raw (truncated): %s",
                        last_raw[:500],
                    )
                    raise RuntimeError(
                        f"LLM extraction failed after {MAX_JSON_REPAIR_ATTEMPTS} repair attempts. "
                        f"Last error: {last_err}\nLast response (truncated): {last_raw[:500]}"
                    ) from last_err
                messages.append({"role": "assistant", "content": last_raw or "(empty response)"})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Your response failed validation with this error:\n{exc}\n\n"
                        "Return ONLY valid JSON that matches the schema. "
                        "No markdown fences, no explanation, no preamble. "
                        f"Schema:\n{schema_snippet}"
                    ),
                })

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
        
        try:
            rsp = self._client.chat.completions.create(**kwargs)
            text = rsp.choices[0].message.content or ""
            return LLMResult(
                value=_StringWrap(text=text),
                model=chosen_model,
                prompt_hash=ph,
                raw_response=rsp.model_dump(),
            )
        except Exception as exc:
            exc_str = str(exc)
            if "402" in exc_str or "Payment Required" in exc_str:
                raise RuntimeError(
                    f"LLM provider quota exceeded (402 Payment Required from {settings.llm_provider})."
                ) from exc
            raise

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
        
        try:
            value = self._instructor.chat.completions.create(**kwargs)
            return LLMResult(value=value, model=chosen_model, prompt_hash=ph)
        except Exception as exc:
            exc_str = str(exc)
            if "402" in exc_str or "Payment Required" in exc_str:
                raise RuntimeError(
                    f"LLM provider quota exceeded (402 Payment Required from {settings.llm_provider})."
                ) from exc
            raise


class _StringWrap(BaseModel):
    text: str


@lru_cache(maxsize=1)
def get_llm_client() -> Any:
    """Return the OpenAI-compatible client (Groq, OpenRouter, Ollama, …).

    Structured extraction uses Instructor JSON mode plus a repair loop when
    validation fails (Llama-class models).
    """
    return LLMClient()

