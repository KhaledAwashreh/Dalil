"""
API-based LLM — provider-agnostic implementation.

Supports two API formats:
- OpenAI-compatible (/v1/chat/completions) — OpenAI, Ollama, vLLM, LM Studio,
  Together AI, Groq, and any other OpenAI-compatible endpoint
- Anthropic Messages API (/v1/messages) — native Claude support

The provider is auto-detected from the base_url or can be set explicitly.
"""

from __future__ import annotations

import logging

import httpx

from dalil.llm.interface import LLMInterface

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior management consultant. "
    "Provide well-structured, evidence-grounded consulting advice."
)


class APILLM(LLMInterface):
    """Multi-provider API LLM client."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        provider: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        timeout: float = 60.0,
    ):
        self._model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def _is_anthropic(self) -> bool:
        return (
            self.provider == "anthropic"
            or "anthropic.com" in self.base_url
        )

    async def generate(self, prompt: str, **kwargs) -> str:
        if self._is_anthropic:
            return await self._generate_anthropic(prompt, **kwargs)
        return await self._generate_openai(prompt, **kwargs)

    async def _generate_openai(self, prompt: str, **kwargs) -> str:
        """OpenAI-compatible chat completions."""
        url = f"{self.base_url}/chat/completions"

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            logger.warning("LLM returned no choices")
            return ""

        return choices[0].get("message", {}).get("content", "")

    async def _generate_anthropic(self, prompt: str, **kwargs) -> str:
        """Anthropic Messages API."""
        url = f"{self.base_url}/messages"

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "x-api-key": self.api_key,
        }

        payload = {
            "model": self._model,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", [])
        if not content:
            logger.warning("Anthropic returned no content")
            return ""

        return content[0].get("text", "")
