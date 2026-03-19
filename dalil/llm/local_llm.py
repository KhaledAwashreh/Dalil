"""
Local LLM — runs a model locally via HuggingFace transformers.

This is a heavier dependency and intended for users who want to run
inference entirely offline/on-premise.
"""

from __future__ import annotations

import logging
from typing import Any

from dalil.llm.interface import LLMInterface

logger = logging.getLogger(__name__)


class LocalLLM(LLMInterface):
    """Local transformer-based LLM using HuggingFace pipeline."""

    def __init__(
        self,
        model_name: str = "mistralai/Mistral-7B-Instruct-v0.2",
        max_tokens: int = 2048,
        temperature: float = 0.3,
        device: str = "auto",
    ):
        self._model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.device = device
        self._pipeline: Any = None

    @property
    def model_name(self) -> str:
        return self._model_name

    def _load(self) -> None:
        if self._pipeline is not None:
            return
        try:
            from transformers import pipeline
        except ImportError:
            raise ImportError(
                "transformers not installed. "
                "Install with: pip install transformers torch"
            )

        logger.info("Loading local model: %s (this may take a while)", self._model_name)
        self._pipeline = pipeline(
            "text-generation",
            model=self._model_name,
            device_map=self.device,
            torch_dtype="auto",
        )
        logger.info("Model loaded: %s", self._model_name)

    async def generate(self, prompt: str, **kwargs) -> str:
        self._load()

        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)

        messages = [
            {"role": "system", "content": "You are a senior management consultant. Provide well-structured, evidence-grounded consulting advice."},
            {"role": "user", "content": prompt},
        ]

        outputs = self._pipeline(
            messages,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            return_full_text=False,
        )

        if outputs and len(outputs) > 0:
            return outputs[0].get("generated_text", "")
        return ""
