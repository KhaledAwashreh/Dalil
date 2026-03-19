"""
Optional local embeddings utility.

MuninnDB handles embeddings internally for storage and retrieval.
This module provides local embedding capability for:
- offline pre-processing or similarity checks outside MuninnDB
- enrichment pipelines that need embeddings before writing to MuninnDB
- fallback if you want to supply pre-computed embeddings on write

Not required for the default retrieval path.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Wrapper around SentenceTransformers for local embedding."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model: Any = None

    def _load(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                logger.info("Loaded embedding model: %s", self.model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Compute embeddings for a list of texts."""
        self._load()
        vectors = self._model.encode(texts, show_progress_bar=False)
        return [v.tolist() for v in vectors]

    def embed_single(self, text: str) -> list[float]:
        return self.embed([text])[0]
