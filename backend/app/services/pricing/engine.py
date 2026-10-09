"""Deterministic pricing + margin engine. The LLM never touches these numbers."""
from __future__ import annotations
import math
from app.config.settings import RANKING


def rooms_needed(adults: int, children: int) -> int:
    return max(1, math.ceil(adults / 2))


def hotel_cost(hotel: dict, nights: int, adults: int, children: int) -> float:
    return hotel["base_price_per_night"] * nights * rooms_needed(adults, children)


def transfer_cost(transfers: list[dict], dest: str, pax: int, kind: str) -> tuple[float, dict | None]:
    """Round-trip airport transfer: private = vehicles needed × price; shared = per person."""
    if kind == "shared":
        t = next((x for x in transfers if x["destination"] == dest and x["kind"] == "airport_shared" and x["availability"]), None)
        return (t["price"] * pax if t else 0.0), t
    cands = sorted([x for x in transfers if x["destination"] == dest and x["kind"] == "airport_private" and x["availability"] and x["capacity"] >= min(pax, 6)], key=lambda x: x["price"])
    if cands:
        return cands[0]["price"], cands[0]
    t = next((x for x in transfers if x["destination"] == dest and x["kind"] == "airport_private" and x["availability"]), None)
    return ((t["price"] * math.ceil(pax / t["capacity"])) if t else 0.0), t


def price_trip(inv, req, hotel: dict, activity_ids: list[str], transfer_type: str = "private", markup: float | None = None, discount: float = 0.0) -> dict:
    """supplier cost → markup → discount → tax → selling price → margin. All floats rounded to 2dp."""
    adults, children = req.travelers.adults, req.travelers.children
    pax, nights = adults + children, req.nights or 0
    hc = hotel_cost(hotel, nights, adults, children)
    ac = sum(inv.activity_by_id[i]["price_per_person"] * pax for i in activity_ids if i in inv.activity_by_id)
    tc, tr = (transfer_cost(inv.transfers, req.destination, pax, transfer_type) if req.transfers_requested else (0.0, None))
    cost = hc + ac + tc
    rate = hotel["margin_pct"] if markup is None else markup
    mk = cost * rate
    pre = cost + mk - discount
    tax = pre * RANKING["tax_rate"]
    total = pre + tax
    margin = mk - discount
    r2 = lambda x: round(x, 2)
    return dict(hotel_cost=r2(hc), activity_cost=r2(ac), transfer_cost=r2(tc), transfer=tr, supplier_cost=r2(cost), markup_rate=round(rate, 4), markup=r2(mk), discount=r2(discount),
                taxes=r2(tax), total=r2(total), gross_margin=r2(margin), margin_pct=r2(margin / pre * 100) if pre else 0.0, rooms=rooms_needed(adults, children), pax=pax)


def budget_optimizer(inv, req, trip_price: dict, hotel: dict, activity_ids: list[str], transfer_type: str, cheaper_hotels: list[dict]) -> dict | None:
    """If over budget, list concrete savings computed with the same pricing engine."""
    if not req.budget or trip_price["total"] <= req.budget:
        return None
    steps, cur, ids, tt = [], trip_price["total"], list(activity_ids), transfer_type
    for h in cheaper_hotels:
        p = price_trip(inv, req, h, ids, tt)
        if p["total"] < cur:
            steps.append(dict(action=f"Change hotel to {h['name']}", saving=round(cur - p["total"], 2))); cur, hotel = p["total"], h; break
    optional = [i for i in ids if i not in req.activity_ids]
    if optional:
        worst = max(optional, key=lambda i: inv.activity_by_id[i]["price_per_person"]); ids.remove(worst)
        p = price_trip(inv, req, hotel, ids, tt); steps.append(dict(action=f"Remove optional activity {inv.activity_by_id[worst]['name']}", saving=round(cur - p["total"], 2))); cur = p["total"]
    if req.transfers_requested and tt != "shared":
        p = price_trip(inv, req, hotel, ids, "shared")
        if p["total"] < cur:
            steps.append(dict(action="Use shared airport transfer", saving=round(cur - p["total"], 2))); cur = p["total"]
    met = cur <= req.budget
    return dict(steps=steps, total_saving=round(trip_price["total"] - cur, 2), optimized_total=round(cur, 2), budget_met=met,
                message="Budget can be met with these changes." if met else "Budget cannot be met without changing a hard constraint.")
