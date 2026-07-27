"""
FAISS vector store wrapper (proposal §2.6, §2.9.2 step 4).

Stores embeddings in a flat FAISS index (cosine similarity via
normalized inner product) plus a parallel JSON metadata file mapping
each vector's position to its chunk_id/document_id/citation info.
Everything is persisted under VECTOR_STORE_DIR so the index survives
a restart without needing to re-embed every document.
"""
import json
import threading
from pathlib import Path
from typing import List, Dict, Any

import faiss
import numpy as np

from backend.config import settings

_INDEX_PATH = Path(settings.VECTOR_STORE_DIR) / "index.faiss"
_META_PATH = Path(settings.VECTOR_STORE_DIR) / "metadata.json"

_lock = threading.Lock()
_EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension


class VectorStore:
    def __init__(self):
        self.index: faiss.Index
        self.metadata: List[Dict[str, Any]] = []
        self._load_or_create()

    def _load_or_create(self):
        if _INDEX_PATH.exists() and _META_PATH.exists():
            self.index = faiss.read_index(str(_INDEX_PATH))
            self.metadata = json.loads(_META_PATH.read_text())
        else:
            self.index = faiss.IndexFlatIP(_EMBEDDING_DIM)
            self.metadata = []

    def _save(self):
        faiss.write_index(self.index, str(_INDEX_PATH))
        _META_PATH.write_text(json.dumps(self.metadata, indent=2))

    def add(self, vectors: np.ndarray, metadatas: List[Dict[str, Any]]) -> List[int]:
        """Adds vectors + metadata, returns the assigned vector positions."""
        with _lock:
            start_pos = self.index.ntotal
            self.index.add(vectors)
            self.metadata.extend(metadatas)
            self._save()
            return list(range(start_pos, start_pos + len(metadatas)))

    def search(self, query_vector: np.ndarray, k: int = 3) -> List[Dict[str, Any]]:
        if self.index.ntotal == 0:
            return []
        query_vector = np.expand_dims(query_vector, axis=0)
        scores, indices = self.index.search(query_vector, min(k, self.index.ntotal))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            meta = dict(self.metadata[idx])
            meta["score"] = float(score)
            results.append(meta)
        return results

    def rebuild(self, vectors: np.ndarray, metadatas: List[Dict[str, Any]]):
        """Wipes the index and rebuilds it from scratch (used by /admin/rebuild-index)."""
        with _lock:
            self.index = faiss.IndexFlatIP(_EMBEDDING_DIM)
            self.metadata = []
            if len(metadatas):
                self.index.add(vectors)
                self.metadata = metadatas
            self._save()

    def count(self) -> int:
        return self.index.ntotal


# Singleton instance used across the app
vector_store = VectorStore()
