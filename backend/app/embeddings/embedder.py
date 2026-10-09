"""Embedding + vector search. Uses sentence-transformers when available; otherwise a deterministic hashed concept embedder."""
from __future__ import annotations
import logging, re, zlib
import numpy as np

log = logging.getLogger("embeddings")
CONCEPTS = [["romantic", "couple", "intimate", "sunset", "honeymoon", "boutique", "quiet", "peaceful", "tranquil"], ["beach", "beachfront", "sea", "coast", "seaside", "shore", "waterfront"],
 ["family", "kid", "child", "pool", "spacious"], ["value", "budget", "cheap", "affordable", "simple", "economical"], ["luxury", "premium", "spa", "fine", "private", "upscale"],
 ["city", "central", "shopping", "metro", "business", "skyline", "downtown"], ["relaxed", "relaxing", "quiet", "peaceful", "slow", "leisure"], ["adventure", "thrill", "safari", "dune", "park"]]
_STOP = {"the", "and", "for", "with", "near", "close", "that", "ideal", "hotel", "property", "stay", "star"}


def _tok(s: str) -> list[str]:
    return [w[:-1] if w.endswith("s") and len(w) > 3 else w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2 and w not in _STOP]


class Embedder:
    """embed_text(list[str]) -> L2-normalised float32 matrix."""

    def __init__(self, backend: str = "auto", model_name: str = "sentence-transformers/all-MiniLM-L6-v2", dim: int = 256):
        self.backend, self.dim, self.model = "hash", dim, None
        if backend in ("auto", "st"):
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_name)
                self.backend, self.dim = "st", self.model.get_sentence_embedding_dimension()
            except Exception as e:  # missing package or no network
                if backend == "st":
                    raise
                log.warning("sentence-transformers unavailable (%s); using hashed concept embedder", type(e).__name__)

    def embed_text(self, texts: list[str]) -> np.ndarray:
        if self.model is not None:
            return np.asarray(self.model.encode(texts, normalize_embeddings=True), dtype="float32")
        out = np.zeros((len(texts), self.dim), dtype="float32")
        for i, t in enumerate(texts):
            for w in _tok(t):
                out[i, zlib.crc32(w.encode()) % self.dim] += 1.0
                for g in CONCEPTS:
                    if w in g:
                        for x in g:
                            if x != w:
                                out[i, zlib.crc32(x.encode()) % self.dim] += .5
        n = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(n == 0, 1, n)


class VectorIndex:
    """FAISS inner-product index over normalised vectors (numpy fallback if faiss missing)."""

    def __init__(self, vectors: np.ndarray, ids: list[str]):
        self.ids, self.vectors = ids, vectors.astype("float32")
        try:
            import faiss
            self._ix = faiss.IndexFlatIP(vectors.shape[1]); self._ix.add(self.vectors)
        except Exception:
            self._ix = None

    def search_similar(self, q: np.ndarray, k: int) -> list[tuple[str, float]]:
        k = min(k, len(self.ids))
        if self._ix is not None:
            sc, ix = self._ix.search(q.reshape(1, -1).astype("float32"), k)
            return [(self.ids[j], float(s)) for s, j in zip(sc[0], ix[0]) if j >= 0]
        sims = self.vectors @ q.astype("float32"); top = np.argsort(-sims)[:k]
        return [(self.ids[j], float(sims[j])) for j in top]
