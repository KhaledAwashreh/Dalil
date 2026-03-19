"""
LLM Interface — the single abstraction all LLM backends implement.

The rest of the application depends ONLY on this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMInterface(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt. Returns the model's response text."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the identifier of the active model."""
        ...
