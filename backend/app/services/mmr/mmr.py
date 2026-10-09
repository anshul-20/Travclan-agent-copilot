"""Maximum Marginal Relevance: MMR = λ·relevance − (1−λ)·max_sim(candidate, selected)."""
from __future__ import annotations
import numpy as np


def mmr_select(relevance: np.ndarray, vectors: np.ndarray, k: int, lam: float = 0.7) -> list[dict]:
    """Return [{index, relevance, diversity, mmr}] in selection order. vectors must be L2-normalised."""
    chosen: list[dict] = []
    remaining = list(range(len(relevance)))
    while remaining and len(chosen) < k:
        best = None
        for i in remaining:
            max_sim = max((float(vectors[i] @ vectors[c["index"]]) for c in chosen), default=0.0)
            val = lam * float(relevance[i]) - (1 - lam) * max_sim
            if best is None or val > best["mmr"]:
                best = dict(index=i, relevance=float(relevance[i]), diversity=1 - max_sim, mmr=val)
        chosen.append(best); remaining.remove(best["index"])
    return chosen


def avg_pairwise_similarity(vectors: np.ndarray) -> float:
    n = len(vectors)
    if n < 2:
        return 0.0
    s = vectors @ vectors.T
    return float((s.sum() - np.trace(s)) / (n * (n - 1)))
