"""Gemini 2.0 Flash LLM client — implements the same interface as LLMClient
but uses the google-genai SDK for extraction, chat, and vision tasks.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from typing import Any, TypeVar

from pydantic import BaseModel
from google import genai
from google.genai import types

from pramaan.config import settings
from pramaan.llm.client import LLMResult, _StringWrap, prompt_hash

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class GeminiClient:
    """Wrapper over google-genai SDK for Gemini 2.0 Flash."""

    def __init__(self) -> None:
        self.mock = settings.is_mock_llm
        if self.mock:
            log.info(
                "Gemini client in MOCK mode — using deterministic stubs."
            )
            self._client = None
        else:
            api_key = settings.gemini_api_key.strip()
            if not api_key or "REPLACE" in api_key:
                log.warning("Gemini API key is missing or invalid. Falling back to mock mode.")
                self.mock = True
                self._client = None
            else:
                self._client = genai.Client(api_key=api_key)

    def extract(
        self,
        *,
        response_model: type[T],
        system: str,
        user: str,
        model: str | None = None,
        prompt_template_version: str = "v1",
        max_retries: int = 2,
    ) -> LLMResult[T]:
        """Structured-output extraction via Gemini."""
        chosen_model = model or settings.gemini_model
        ph = prompt_hash(
            system + "\n\n---\n\n" + user,
            model=chosen_model,
            schema=response_model.__name__,
            template_version=prompt_template_version,
            temperature=settings.llm_temperature,
        )

        if self.mock:
            from pramaan.llm.mock import fake_extract
            value = fake_extract(response_model, system=system, user=user)
            return LLMResult(value=value, model=f"mock://{chosen_model}", prompt_hash=ph)

        assert self._client is not None
        t0 = time.perf_counter()
        
        # We need to construct the schema for Gemini
        schema = response_model.model_json_schema()
        
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_tokens,
            response_mime_type="application/json",
            response_schema=schema,
        )
        
        try:
            log.info(
                "gemini.extract start (model=%s schema=%s)",
                chosen_model,
                response_model.__name__,
            )
            
            response = self._client.models.generate_content(
                model=chosen_model,
                contents=[user],
                config=config,
            )
            
            # Parse the JSON response back into the Pydantic model
            text = response.text
            if not text:
                raise ValueError("Empty response from Gemini")
                
            value = response_model.model_validate_json(text)
            
            dt = time.perf_counter() - t0
            log.info(
                "gemini.extract ok (model=%s schema=%s prompt_hash=%s elapsed_s=%.2f)",
                chosen_model,
                response_model.__name__,
                ph[:12],
                dt,
            )
            return LLMResult(value=value, model=chosen_model, prompt_hash=ph)
        except Exception as exc:
            dt = time.perf_counter() - t0
            log.exception(
                "gemini.extract failed (model=%s schema=%s elapsed_s=%.2f prompt_hash=%s)",
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
        """Free-form chat."""
        chosen_model = model or settings.gemini_model
        ph = prompt_hash(
            system + "\n\n---\n\n" + user,
            model=chosen_model,
            template_version=prompt_template_version,
            temperature=settings.llm_temperature,
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
        
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_tokens,
        )
        
        response = self._client.models.generate_content(
            model=chosen_model,
            contents=[user],
            config=config,
        )
        
        return LLMResult(
            value=_StringWrap(text=response.text or ""),
            model=chosen_model,
            prompt_hash=ph,
            raw_response={"text": response.text},
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
        """VLM call for images."""
        chosen_model = model or settings.gemini_model
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

        assert self._client is not None
        
        # Create parts from text and base64 images
        import base64
        parts = [user]
        for b64 in image_b64s:
            parts.append(
                types.Part.from_bytes(
                    data=base64.b64decode(b64),
                    mime_type="image/png"
                )
            )
            
        schema = response_model.model_json_schema()
        
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_tokens,
            response_mime_type="application/json",
            response_schema=schema,
        )
        
        response = self._client.models.generate_content(
            model=chosen_model,
            contents=parts,
            config=config,
        )
        
        text = response.text
        if not text:
            raise ValueError("Empty response from Gemini")
            
        value = response_model.model_validate_json(text)
        return LLMResult(value=value, model=chosen_model, prompt_hash=ph)
