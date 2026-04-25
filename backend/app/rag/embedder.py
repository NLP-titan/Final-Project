"""Sentence-transformer embedder.

Loaded lazily and cached as a module-level singleton — the model is several hundred MB and
shouldn't be reinstantiated per request.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable

from app.config import settings


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    model = _get_model()
    vectors = model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
