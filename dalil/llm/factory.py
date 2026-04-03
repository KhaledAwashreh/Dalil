"""
LLM Factory — instantiates the correct LLM backend from config.
"""

from __future__ import annotations

from dalil.config.settings import LLM_PROVIDER_BASE_URLS, LLMSettings
from dalil.llm.interface import LLMInterface


def create_llm(settings: LLMSettings) -> LLMInterface:
    """Create an LLM instance from settings.

    Config examples:

    Local (transformers):
        {"type": "local", "model": "mistralai/Mistral-7B-Instruct-v0.2"}

    Ollama:
        {"type": "api", "provider": "ollama", "model": "mistral",
         "base_url": "http://localhost:11434/v1"}

    OpenAI:
        {"type": "api", "provider": "openai", "model": "gpt-4o",
         "api_key": "sk-..."}

    Anthropic (native):
        {"type": "api", "provider": "anthropic", "model": "claude-sonnet-4-20250514",
         "api_key": "sk-ant-..."}

    vLLM / LM Studio / any OpenAI-compatible:
        {"type": "api", "model": "my-model",
         "base_url": "http://localhost:8000/v1"}
    """
    if settings.type == "local":
        from dalil.llm.local_llm import LocalLLM

        return LocalLLM(
            model_name=settings.model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )

    # Default: API-based (OpenAI-compatible)
    from dalil.llm.api_llm import APILLM

    # Provider-specific base_url defaults
    base_url = settings.base_url
    if not base_url:
        base_url = LLM_PROVIDER_BASE_URLS.get(
            settings.provider, "https://api.openai.com/v1"
        )

    return APILLM(
        model=settings.model,
        api_key=settings.api_key,
        base_url=base_url,
        provider=settings.provider,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )
