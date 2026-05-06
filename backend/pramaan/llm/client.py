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
            log.info("LLM client running in MOCK mode (no API key, or LLM_MOCK=1)")
            self._client: OpenAI | None = None
            self._instructor: Any | None = None
        else:
            base = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
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
        value = self._instructor.chat.completions.create(
            model=chosen_model,
            response_model=response_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=settings.llm_temperature,
            seed=settings.llm_seed,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_s,
            max_retries=max_retries,
        )
        return LLMResult(value=value, model=chosen_model, prompt_hash=ph)

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
        rsp = self._client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=settings.llm_temperature,
            seed=settings.llm_seed,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_s,
        )
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
        value = self._instructor.chat.completions.create(
            model=chosen_model,
            response_model=response_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            temperature=settings.llm_temperature,
            seed=settings.llm_seed,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_s,
        )
        return LLMResult(value=value, model=chosen_model, prompt_hash=ph)


class _StringWrap(BaseModel):
    text: str


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    return LLMClient()
