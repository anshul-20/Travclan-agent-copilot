"""Two-stage retrieval: (1) hard filters + FAISS semantic retrieval, (2) explainable weighted ranking."""
from __future__ import annotations
import numpy as np
from app.config.settings import RANKING
from app.embeddings.embedder import Embedder, VectorIndex
from app.services.pricing.engine import hotel_cost
from app.services.supplier.health import supplier_risks


def hard_filter_hotels(hotels: list[dict], req) -> tuple[list[dict], dict]:
    """HARD constraints only: destination, availability, min stars, hotel cost <= share of budget."""
    a, c = req.travelers.adults, req.travelers.children
    cap = req.budget * RANKING["hotel_budget_share"] if req.budget else None
    rejected = {"availability": 0, "star_rating": 0, "budget": 0}
    out = []
    for h in hotels:
        if h["destination"] != req.destination:
            continue
        if not h["availability"]:
            rejected["availability"] += 1; continue
        if req.hotel_star_rating and h["star_rating"] < req.hotel_star_rating:
            rejected["star_rating"] += 1; continue
        if cap and hotel_cost(h, req.nights or 1, a, c) > cap:
            rejected["budget"] += 1; continue
        out.append(h)
    return out, rejected


def query_text(req) -> str:
    """Natural-language query used for semantic matching (soft preferences)."""
    t = [req.raw_text, req.travel_style]
    if req.travelers.adults == 2 and not req.travelers.children:
        t.append("romantic couple")
    if req.travelers.children:
        t.append("family kids")
    return " ".join(t)


class HotelRetriever:
    def __init__(self, inv, embedder: Embedder):
        self.inv, self.emb = inv, embedder
        vecs = embedder.embed_text([h["description"] for h in inv.hotels])
        self.vec = {h["id"]: vecs[i] for i, h in enumerate(inv.hotels)}
        self.index: dict[str, VectorIndex] = {}
        for d in {h["destination"] for h in inv.hotels}:
            hs = [h["id"] for h in inv.hotels if h["destination"] == d]
            self.index[d] = VectorIndex(np.stack([self.vec[i] for i in hs]), hs)

    def semantic(self, req, ids: set[str]) -> dict[str, float]:
        """Stage 1b: FAISS cosine similarity over the destination index, restricted to hard-filtered ids."""
        q = self.emb.embed_text([query_text(req)])[0]
        res = self.index[req.destination].search_similar(q, 10_000)
        return {i: s for i, s in res if i in ids}

    def rank(self, req, objective: str | None = None) -> tuple[list[dict], dict]:
        objective = objective or RANKING["objective"]
        W = dict(RANKING["weights"]); bw = RANKING["biz_weight"][objective]
        W["sem"] -= bw - W["biz"]; W["biz"] = bw
        cands, rej = hard_filter_hotels(self.inv.hotels, req)
        if not cands:
            return [], rej
        sem = self.semantic(req, {h["id"] for h in cands})
        lo, hi = min(sem.values()), max(sem.values())
        cap = req.budget * RANKING["hotel_budget_share"] if req.budget else None
        out = []
        for h in cands:
            hc = hotel_cost(h, req.nights or 1, req.travelers.adults, req.travelers.children)
            sup = self.inv.suppliers[h["supplier_id"]]
            couple = req.travelers.adults == 2 and not req.travelers.children
            pref = (.5 if couple and h["couple_friendly"] else .2) + (.6 if req.travelers.children and h["family_friendly"] else 0) + (.3 if req.travel_style == "relaxed" and h["hotel_type"] in ("beach", "couple", "luxury") else 0) + (.2 if req.hotel_star_rating == h["star_rating"] else 0)
            f = dict(sem=(sem[h["id"]] - lo) / ((hi - lo) or 1), budget=(1 - .4 * (hc / cap) ** 3) if cap else .5, rating=(h["rating"] - 3) / 2, avail=1.0, pref=min(1.0, pref),
                     supplier=sup["health"] / 100, loc=h["location_score"], biz=min(1.0, max(0.0, (h["margin_pct"] - .06) / .1)))
            out.append(dict(hotel=h, features=f, score=sum(W[k] * f[k] for k in W), raw_similarity=sem[h["id"]], hotel_cost=hc, supplier_health=sup["health"], risks=supplier_risks(sup), weights=W))
        out.sort(key=lambda x: -x["score"])
        return out, rej
