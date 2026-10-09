"""Offline evaluation on SYNTHETIC queries. Every number printed is computed here; nothing is hard-coded.
Relevance-labelled metrics (Recall/NDCG/MRR) are intentionally omitted: they need human-judged relevance labels."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import numpy as np
from app.main import build_engine
from app.services.mmr.mmr import avg_pairwise_similarity
from app.services.requirement_extraction.extractor import extract_requirement
from app.services.itinerary.planner import build_itinerary, itinerary_conflicts, select_activities
from app.services.pricing.engine import hotel_cost, price_trip
from app.services.validation.validator import validate_trip

STY = ["relaxed", "balanced", "packed"]
FORMS = ["Need a {n} night {d} trip for {a} adults, budget {l} lakh, {s} trip, 4 star hotel", "{a} adults want {n1} days in {d} around ₹{b:,}. {s} pace please, 4-star", "Plan {d} for {a} adults, {n} nights, {k}k budget. We prefer a {s} itinerary. 4 star"]


def scenarios(n=120, seed=7):
    rng = np.random.default_rng(seed); dests = ["Dubai", "Singapore", "Bangkok", "Bali", "Maldives", "Paris", "London", "Japan"]
    for i in range(n):
        d, nn, a, s = str(rng.choice(dests)), int(rng.integers(3, 9)), int(rng.integers(1, 5)), str(rng.choice(STY))
        b = int(rng.integers(60, 200)) * 1000
        yield dict(text=FORMS[i % 3].format(d=d, n=nn, n1=nn + 1, a=a, s=s, b=b, l=b / 100000, k=b // 1000), dest=d, nights=nn, adults=a, budget=b)


def main():
    eng = build_engine(); inv = eng.inv; names = list(inv.destinations); S = list(scenarios())
    json.dump(S, open(ROOT / "data" / "evaluation" / "scenarios.json", "w"), indent=1)
    ok = dict(destination=0, nights=0, budget=0, adults=0); agg = {k: dict(sim=[], div=[], bv=0, av=0, n=0, empty=0) for k in ("mmr", "no_mmr")}
    feas = quote_err = viol = 0; ran = 0
    for s in S:
        r = extract_requirement(s["text"], names, inv.activities).requirement
        ok["destination"] += r.destination == s["dest"]; ok["nights"] += r.nights == s["nights"]; ok["budget"] += r.budget == s["budget"]; ok["adults"] += r.travelers.adults == s["adults"]
        for key, use in (("mmr", True), ("no_mmr", False)):
            res = eng.recommend(r, use_mmr=use); g = agg[key]
            if not res["items"]:
                g["empty"] += 1; continue
            ids = [i["hotel_id"] for i in res["items"]]
            g["sim"].append(avg_pairwise_similarity(np.stack([eng.retriever.vec[i] for i in ids]))); g["div"].append(1 - g["sim"][-1])
            g["bv"] += sum(inv.hotel_by_id[i]["destination"] != r.destination or hotel_cost(inv.hotel_by_id[i], r.nights, r.travelers.adults, 0) > r.budget * .6 for i in ids) / len(ids)
            g["av"] += sum(not inv.hotel_by_id[i]["availability"] for i in ids) / len(ids); g["n"] += 1
        res = eng.recommend(r)
        if res["items"]:
            trip = eng.start_trip(r); q = eng.quote(trip); ran += 1
            feas += not itinerary_conflicts(q["itinerary"], r.travel_style)
            p = q["pricing"]; quote_err += abs((p["supplier_cost"] + p["markup"] - p["discount"]) * 1.05 - p["total"]) > .05
            viol += any(v["status"] == "fail" and v["check"] in ("Hotel availability", "Hotel rating", "Activity availability") for v in q["validation"])
    n = len(S); pc = lambda x, d=n: f"{100 * x / d:.1f}%"
    print(f"Scenarios: {n} synthetic | embedding backend: {eng.emb.backend}")
    print("Extraction accuracy:", {k: pc(v) for k, v in ok.items()})
    print(f"Quotes generated: {ran}/{n} | itinerary feasibility {pc(feas, ran)} | price recompute errors {quote_err} | hard-constraint violations {viol}")
    print("Top-5 hotels (higher diversity / lower similarity = more diverse):")
    for k, g in agg.items():
        if g["n"]:
            print(f"  {k:7s} avg_pairwise_sim={np.mean(g['sim']):.3f} diversity@5={np.mean(g['div']):.3f} budget_violation_rate={g['bv'] / g['n']:.3f} availability_violation_rate={g['av'] / g['n']:.3f} (queries with results {g['n']}, empty {g['empty']})")


if __name__ == "__main__":
    main()
