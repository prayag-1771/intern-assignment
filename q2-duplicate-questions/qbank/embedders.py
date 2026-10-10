"""Turn question text into vectors ("embeddings") so questions can be compared by meaning.

Every embedder returns one row per input text, scaled to length 1. With rows of
length 1, the cosine similarity of two questions is the dot product of their rows.
"""

from __future__ import annotations

import os
import time
from typing import Protocol, Sequence

import numpy as np
import requests

from .config import api_key


class Embedder(Protocol):
    """Anything that can turn texts into unit-length vectors."""

    name: str

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Return an array of shape (len(texts), dimensions)."""
        ...


def _unit_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return (matrix / np.clip(norms, 1e-12, None)).astype(np.float32)


class LocalEmbedder:
    """A sentence-transformers model that runs on this machine. No API key, no network after download."""

    def __init__(self, model_name: str, prompt: str | None = None, device: str | None = None):
        # Imported here so the rest of the package loads without this heavy dependency.
        from sentence_transformers import SentenceTransformer

        # QBANK_DEVICE=cpu or QBANK_DEVICE=cuda pins the device; otherwise the library chooses.
        device = device or os.environ.get("QBANK_DEVICE") or None
        self._model = SentenceTransformer(model_name, device=device)
        self._prompt = prompt
        self.name = model_name if prompt is None else f"{model_name} + instruction"
        self.device = str(self._model.device)

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        vectors = self._model.encode(
            list(texts),
            prompt=self._prompt,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return _unit_rows(np.asarray(vectors))


class GeminiEmbedder:
    """Google's hosted embedding model. Needs GEMINI_API_KEY and an internet connection."""

    _URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
    _RETRYABLE = (429, 500, 503)
    _ATTEMPTS = 4

    def __init__(self, model: str = "gemini-embedding-001", task_type: str = "SEMANTIC_SIMILARITY"):
        key = api_key("GEMINI_API_KEY")
        if key is None:
            raise RuntimeError("GEMINI_API_KEY is not set; add it to .env to use GeminiEmbedder.")
        self._key = key
        self._model = model
        self._task_type = task_type
        self.name = model
        self.device = "api"

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        return _unit_rows(np.array([self._embed_one(text) for text in texts], dtype=np.float32))

    def _embed_one(self, text: str) -> list[float]:
        body = {
            "model": f"models/{self._model}",
            "content": {"parts": [{"text": text}]},
            "taskType": self._task_type,
        }
        for attempt in range(self._ATTEMPTS):
            response = requests.post(
                self._URL.format(model=self._model),
                headers={"x-goog-api-key": self._key},
                json=body,
                timeout=60,
            )
            # Rate limits and brief server errors are worth another try; anything else is a real failure.
            if response.status_code not in self._RETRYABLE or attempt == self._ATTEMPTS - 1:
                break
            time.sleep(2**attempt)
        response.raise_for_status()
        return response.json()["embedding"]["values"]
