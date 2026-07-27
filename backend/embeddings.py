"""
Embedding generation module (proposal §2.9.2 step 3, §2.6).

Wraps a local SentenceTransformers model so all embedding happens
on-device — no text is ever sent to an external API.
"""
from functools import lru_cache
from typing import List

import numpy as np

from backend.config import settings


@lru_cache(maxsize=1)
def _load_model():
    # Imported lazily so the rest of the API can start even before the
    # (fairly large) sentence-transformers dependency finishes importing.
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts: List[str]) -> np.ndarray:
    """Returns an (N, D) float32 numpy array of normalized embeddings."""
    if not texts:
        return np.zeros((0, 384), dtype="float32")
    model = _load_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vectors, dtype="float32")


def embed_query(text: str) -> np.ndarray:
    return embed_texts([text])[0]
