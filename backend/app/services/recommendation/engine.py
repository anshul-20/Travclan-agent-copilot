"""Orchestrator: requirement → ranked+diversified options → itinerary → price → validation → quote. Deterministic code drives everything."""
from __future__ import annotations
import re, time
import numpy as np
from app.config.settings import RANKING
from app.schemas.schemas import Requirement, Trip
from app.services.itinerary.planner import build_itinerary, select_activities
from app.services.mmr.mmr import mmr_select
from app.services.pricing.engine import budget_optimizer, price_trip
from app.services.ranking.ranker import HotelRetriever
from app.services.validation.validator import validate_trip


class CopilotEngine:
    def __init__(self, inv, embedder):
        self.inv, self.emb = inv, embedder
        self.retriever = HotelRetriever(inv, embedder)

    # ---- recommendations -------------------------------------------------
    def recommend(self, req: Requirement, lam: float | None = None, objective: str | None = None, use_mmr: bool = True, k: int = 5) -> dict:
        t0 = time.perf_counter()
        ranked, rejected = self.retriever.rank(req, objective)
        if not ranked:
            return dict(items=[], rejected=rejected, message="No available hotel satisfies the hard constraints (destination, stars, availability, budget share).", latency_ms=0)
        lam = RANKING["mmr_lambda"] if lam is None else lam
        pool = ranked[:25]
        if use_mmr:
            vecs = np.stack([self.retriever.vec[x["hotel"]["id"]] for x in pool])
            sel = mmr_select(np.array([x["score"] for x in pool]), vecs, k, lam)
            picked = [dict(pool[s["index"]], relevance=s["relevance"], diversity=s["diversity"], mmr=s["mmr"]) for s in sel]
        else:
            picked = [dict(x, relevance=x["score"], diversity=None, mmr=None) for x in ranked[:k]]
        items = []
        for x in picked:
            h = x["hotel"]; p = price_trip(self.inv, req, h, select_activities(self.inv, req, h), "private")
            items.append(dict(hotel_id=h["id"], name=h["name"], star_rating=h["star_rating"], area=h["area"], hotel_type=h["hotel_type"], rating=h["rating"],
                              estimated_total=p["total"], estimated_margin=p["gross_margin"], above_budget=bool(req.budget and p["total"] > req.budget), supplier_risk=x["risks"],
                              scores=dict(final=round(x["score"], 3), semantic_raw=round(x["raw_similarity"], 3), relevance=round(x["relevance"], 3), diversity=None if x["diversity"] is None else round(x["diversity"], 3),
                                          mmr=None if x["mmr"] is None else round(x["mmr"], 3), **{k2: round(v, 3) for k2, v in x["features"].items()}),
                              explanation=self._why(req, x)))
        labels = self._label(items)
        for it in items:
            it["category"] = labels.get(it["hotel_id"], "ALTERNATIVE")
        return dict(items=items, rejected=rejected, candidates_after_hard_filters=len(ranked), mmr_lambda=lam if use_mmr else None, embedding_backend=self.emb.backend,
                    latency_ms=round((time.perf_counter() - t0) * 1000, 1))

    @staticmethod
    def _label(items: list[dict]) -> dict[str, str]:
        """Each label is won independently (so BEST MATCH can also be BEST VALUE); unlabeled items are ALTERNATIVE."""
        keys = [("BEST MATCH", lambda i: -i["scores"]["final"]), ("BEST VALUE", lambda i: i["estimated_total"]),
                ("BEST EXPERIENCE", lambda i: -(i["rating"] * i["star_rating"])), ("PREMIUM", lambda i: -i["estimated_total"])]
        out: dict[str, list[str]] = {}
        for lab, key in keys:
            out.setdefault(min(items, key=key)["hotel_id"], []).append(lab)
        return {i["hotel_id"]: " + ".join(out[i["hotel_id"]]) if i["hotel_id"] in out else "ALTERNATIVE" for i in items}

    @staticmethod
    def _why(req, x) -> str:
        h, parts = x["hotel"], []
        if req.hotel_star_rating and h["star_rating"] >= req.hotel_star_rating:
            parts.append(f"meets the {req.hotel_star_rating}-star requirement ({h['star_rating']}★)")
        if req.budget:
            parts.append(f"hotel cost ₹{x['hotel_cost']:,.0f} is {x['hotel_cost'] / req.budget:.0%} of the budget")
        parts.append(f"rated {h['rating']} from {h['review_count']} reviews")
        if h["couple_friendly"] and req.travelers.adults == 2 and not req.travelers.children:
            parts.append("suits couples")
        parts.append(f"located in {h['area']}")
        if x["supplier_health"] >= 85:
            parts.append(f"supplier health {x['supplier_health']}/100")
        return "Recommended because it " + ", ".join(parts) + "."

    # ---- trip / quote ----------------------------------------------------
    def start_trip(self, req: Requirement, hotel_id: str | None = None) -> Trip:
        if hotel_id is None:
            ranked, _ = self.retriever.rank(req)
            if not ranked:
                raise ValueError("No hotel satisfies the hard constraints")
            hotel_id = ranked[0]["hotel"]["id"]
        return Trip(requirement=req, hotel_id=hotel_id, activity_ids=select_activities(self.inv, req, self.inv.hotel_by_id[hotel_id]))

    def quote(self, trip: Trip) -> dict:
        t0 = time.perf_counter(); req = trip.requirement
        hotel = self.inv.hotel_by_id[trip.hotel_id]
        it = build_itinerary(self.inv, req, hotel, trip.activity_ids)
        p = price_trip(self.inv, req, hotel, trip.activity_ids, trip.transfer_type, trip.markup, trip.discount)
        v = validate_trip(self.inv, req, hotel, trip.activity_ids, it, p)
        cheaper = [x["hotel"] for x in sorted(self.retriever.rank(req)[0], key=lambda x: -x["score"]) if x["hotel"]["base_price_per_night"] < hotel["base_price_per_night"]]
        opt = budget_optimizer(self.inv, req, p, hotel, trip.activity_ids, trip.transfer_type, cheaper)
        sup = self.inv.suppliers[hotel["supplier_id"]]
        return dict(trip=trip.model_dump(), itinerary=it, pricing=p, validation=v, budget_optimizer=opt, ready_to_send=not any(x["status"] == "fail" for x in v),
                    summary=dict(destination=req.destination, nights=req.nights, month=req.month, travelers=req.travelers.model_dump(), hotel=dict(name=hotel["name"], star=hotel["star_rating"], area=hotel["area"], meal_plan=hotel["meal_plan"], cancellation=hotel["cancellation_policy"]),
                                 activities=[self.inv.activity_by_id[i]["name"] for i in trip.activity_ids if i in self.inv.activity_by_id], supplier_health=sup["health"]),
                    disclaimer="Synthetic demo data. Not an official quotation; availability and prices are illustrative.", latency_ms=round((time.perf_counter() - t0) * 1000, 1))

    # ---- conversational modification ------------------------------------
    def modify(self, trip: Trip, command: str) -> dict:
        """Apply a command to the structured trip (no full regeneration) and report before/after."""
        before = self.quote(trip); c = command.lower(); req = trip.requirement.model_copy(deep=True); new = trip.model_copy(deep=True, update={"requirement": req}); note = None
        if re.search(r"relax", c):
            req.travel_style = "relaxed"
            keep = [i for i in new.activity_ids if i in req.activity_ids]
            extras = select_activities(self.inv, req, None)
            new.activity_ids = keep + [i for i in extras if i not in keep][: max(0, len(extras) - len(keep))]; note = "Made itinerary more relaxed; optional activities trimmed"
        elif re.search(r"cheap|replace.*hotel|better value|lower.*price|reduce.*price", c):
            cur = self.inv.hotel_by_id[trip.hotel_id]["base_price_per_night"]
            ranked, _ = self.retriever.rank(req)
            alt = next((x for x in ranked if x["hotel"]["base_price_per_night"] < cur), None)
            if not alt:
                return dict(before=before, after=before, note="No cheaper hotel satisfies the hard constraints.", changed=False)
            new.hotel_id = alt["hotel"]["id"]; note = f"Replaced hotel with {alt['hotel']['name']}; activities kept"
        elif m := re.match(r"\s*(?:add|include)\s+(?:a|an|the)?\s*(.+)", c):
            a = self._find_activity(req.destination, m.group(1), exclude=new.activity_ids)
            if not a:
                return dict(before=before, after=before, note="No matching activity found in this destination.", changed=False)
            new.activity_ids.append(a["id"]); note = f"Added {a['name']}"
        elif m := re.match(r"\s*(?:remove|drop|delete)\s+(?:a|an|the)?\s*(.+)", c):
            a = self._find_activity(req.destination, m.group(1), only=new.activity_ids)
            if not a:
                return dict(before=before, after=before, note="That activity is not in the plan.", changed=False)
            new.activity_ids.remove(a["id"]); req.activity_ids = [i for i in req.activity_ids if i != a["id"]]; note = f"Removed {a['name']}"
        elif m := re.search(r"markup\D{0,6}(\d+(?:\.\d+)?)", c):
            new.markup = float(m.group(1)) / 100; note = f"Markup set to {m.group(1)}%"
        elif m := re.search(r"discount\D{0,6}(\d+)", c):
            new.discount = float(m.group(1)); note = f"Discount ₹{m.group(1)} applied"
        else:
            return dict(before=before, after=before, note="Command not understood. Try: replace hotel with something cheaper, add/remove an activity, make it more relaxed, set markup 8%.", changed=False)
        after = self.quote(new)
        return dict(before=before, after=after, note=note, changed=True, delta=dict(price=round(after["pricing"]["total"] - before["pricing"]["total"], 2), margin=round(after["pricing"]["gross_margin"] - before["pricing"]["gross_margin"], 2)))

    def _find_activity(self, dest, text, exclude=(), only=None):
        words = [w for w in re.findall(r"[a-z]{4,}", text) if w not in ("activity", "activities", "from", "plan")]
        pool = [a for a in self.inv.activities_in(dest) if (only is None or a["id"] in only) and a["id"] not in exclude]
        return next((a for a in pool if any(w in a["name"].lower() or re.search(a["keywords"], w) for w in words)), None)
