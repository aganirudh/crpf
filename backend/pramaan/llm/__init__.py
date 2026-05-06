"""LLM client layer.

Provider-agnostic: as long as the endpoint speaks OpenAI Chat Completions
(OpenAI, OpenRouter, Groq, Together, Fireworks, Ollama, vLLM…) PRAMAAN can
talk to it. Swappable via env vars at startup.

For development without an API key, set `PRAMAAN_LLM_MOCK=1` to use the
deterministic stub in `mock.py`.
"""

from pramaan.llm.client import LLMClient, get_llm_client, prompt_hash

__all__ = ["LLMClient", "get_llm_client", "prompt_hash"]
