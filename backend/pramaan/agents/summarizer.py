"""Summarizer Agent — translates structured evaluation payloads into
readable narratives using Gemini 2.0 Flash.

Spec: Phase 6 of implementation plan.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from pramaan.config import settings
from pramaan.llm.client import get_llm_client

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Pramaan Analysis Engine, an expert technical evaluator for the Central Reserve Police Force (CRPF) procurement system.
Your task is to generate a comprehensive, professional, and clear narrative summary of a bidder's evaluation.
You will be provided with a transparent JSON payload containing the exact findings of the Pramaan Reasoning Engine.

Your summary MUST cover these sections in order:
1. Overview (bidder name and tender reference)
2. Financial Assessment (turnover, net worth)
3. Technical Qualification (projects, engineer, equipment)
4. Compliance Status (statutory documents)
5. Optional Technical Score (points breakdown)
6. Recommendation (Overall verdict and next steps)

Guidelines:
- Use Markdown formatting with `###` for section headers.
- Use bullet points for readability where appropriate.
- Highlight key numbers and verdicts in bold.
- If there are criteria "UNDER REVIEW", clearly state what is pending manual verification.
- Be objective, precise, and authoritative. Do not hallucinate any information not present in the JSON.
- Never mention "JSON", "Reasoning Engine", or "Prompt". Speak directly as the Analysis Engine.
"""

class Summarizer:
    def __init__(self) -> None:
        self.llm = get_llm_client()

    def generate_summary(self, payload: dict[str, Any]) -> str:
        """Generate a narrative summary from an evaluation payload."""
        log.info("Summarizer generating analysis for payload")
        
        user_prompt = f"""Generate the evaluation summary for the following bidder based on this engine payload:

{json.dumps(payload, indent=2)}"""

        # We use chat() for free-form narrative generation
        result = self.llm.chat(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            prompt_template_version="v1.0"
        )
        
        log.info(f"Summary generated successfully using model {result.model}")
        return result.value.text
