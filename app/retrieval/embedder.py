"""Local sentence embeddings (no API key, no cost): fastembed runs a small ONNX model on CPU.

bge-small-en-v1.5 is 384-dimensional and ~130 MB. Queries and passages are embedded differently
(the model expects a search instruction on queries), which fastembed handles via query_embed.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np


class Embedder:
    def __init__(self, model_name: str, cache_dir: Path):
        from fastembed import TextEmbedding  # imported lazily: optional dependency

        cache_dir.mkdir(parents=True, exist_ok=True)
        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name, cache_dir=str(cache_dir))

    def passages(self, texts: list[str]) -> np.ndarray:
        return _normalise(np.array(list(self._model.passage_embed(texts)), dtype="float32"))

    def queries(self, texts: list[str]) -> np.ndarray:
        return _normalise(np.array(list(self._model.query_embed(texts)), dtype="float32"))


def _normalise(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.clip(norms, 1e-12, None)


@lru_cache(maxsize=2)
def get_embedder(model_name: str, cache_dir: str) -> Embedder:
    return Embedder(model_name, Path(cache_dir))
