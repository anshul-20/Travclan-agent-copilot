"""Constraint validator: budget, availability, duration, rating, capacity, schedule, pricing integrity, supplier risk."""
from __future__ import annotations
from app.config.settings import RANKING
from app.services.itinerary.planner import itinerary_conflicts
from app.services.supplier.health import supplier_risks


def validate_trip(inv, req, hotel: dict, activity_ids: list[str], it: dict, price: dict) -> list[dict]:
    """Return [{check, status: pass|warn|fail, detail}]. 'fail' blocks sending; 'warn' needs agent attention."""
    out = []
    add = lambda c, s, d: out.append(dict(check=c, status=s, detail=d))
    if req.budget is None:
        add("Budget", "warn", "No budget provided")
    elif price["total"] <= req.budget:
        add("Budget", "pass", f"₹{price['total']:,.0f} within ₹{req.budget:,.0f}")
    else:
        add("Budget", "fail", f"₹{price['total']:,.0f} exceeds ₹{req.budget:,.0f} by ₹{price['total'] - req.budget:,.0f}")
    add("Hotel availability", "pass" if hotel["availability"] else "fail", "Available per synthetic inventory" if hotel["availability"] else "Availability cannot be confirmed")
    if req.hotel_star_rating:
        add("Hotel rating", "pass" if hotel["star_rating"] >= req.hotel_star_rating else "fail", f"{hotel['star_rating']}★ vs required {req.hotel_star_rating}★")
    missing = [i for i in activity_ids if i not in inv.activity_by_id]
    na = [inv.activity_by_id[i]["name"] for i in activity_ids if i in inv.activity_by_id and not inv.activity_by_id[i]["availability"]]
    add("Activity availability", "fail" if (na or missing) else "pass", ", ".join(na) + (" unavailable" if na else "") if (na or missing) else "All selected activities available")
    conf = itinerary_conflicts(it, req.travel_style)
    add("Schedule", "fail" if conf else "pass", "; ".join(conf) if conf else "No overlaps; daily load within style limits")
    add("Duration", "pass" if len(it["days"]) == (req.nights or 0) + 1 else "fail", f"{req.nights} nights / {(req.nights or 0) + 1} days")
    pax = req.travelers.adults + req.travelers.children
    add("Traveler capacity", "pass" if pax <= price["rooms"] * 3 else "fail", f"{pax} travelers in {price['rooms']} room(s)")
    if req.transfers_requested:
        add("Transfer feasibility", "pass" if price["transfer"] else "fail", price["transfer"]["vehicle_type"] if price["transfer"] else "No available transfer in inventory")
    recomputed = round((price["supplier_cost"] + price["markup"] - price["discount"]) * (1 + RANKING["tax_rate"]), 2)
    add("Price & margin", "pass" if abs(recomputed - price["total"]) < .05 and price["gross_margin"] >= 0 else "fail", "Recomputed deterministically")
    risks = supplier_risks(inv.suppliers[hotel["supplier_id"]])
    add("Supplier risk", "warn" if risks else "pass", "; ".join(risks) if risks else "Supplier metrics healthy")
    return out
