"""Itinerary generation: respects style caps/hours, clusters nearby activities, accounts for travel time."""
from __future__ import annotations
from app.config.settings import RANKING
from app.utils.geo import haversine_km


def select_activities(inv, req, hotel: dict | None = None, extra_ok: bool = True) -> list[str]:
    """Requested activities first (always kept), then top-rated extras up to a style-dependent target."""
    style, nights = req.travel_style, req.nights or 1
    free_days = max(nights - 1, 1)
    cap = RANKING["activities_per_day"][style]
    target = max(len(req.activity_ids), min(cap * free_days - 1, round(cap * free_days * (.35 if style == "relaxed" else .6))))
    ids = [i for i in req.activity_ids if i in inv.activity_by_id and inv.activity_by_id[i]["availability"]]
    if extra_ok:
        extras = sorted([a for a in inv.activities_in(req.destination) if a["id"] not in ids and a["availability"]], key=lambda a: -(a["rating"] + a["popularity_score"]))
        for a in extras:
            if len(ids) >= target:
                break
            ids.append(a["id"])
    # prune optional extras that cannot be scheduled within the style's daily limits (requested ones are always kept)
    while True:
        over = set(a for a in build_itinerary(inv, req, hotel or {}, ids)["overflow"])
        drop = [i for i in ids if inv.activity_by_id[i]["name"] in over and i not in req.activity_ids]
        if not drop:
            return ids
        ids.remove(drop[-1])


def build_itinerary(inv, req, hotel: dict, activity_ids: list[str]) -> dict:
    """Return {days:[{day,kind,items,hours,travel_minutes}], overflow:[names]}."""
    nights = req.nights or 0
    cap, hmax, spd = RANKING["activities_per_day"][req.travel_style], RANKING["hours_per_day"][req.travel_style], RANKING["travel_speed_kmh"]
    days = [dict(day=d, kind="arrival" if d == 1 else "departure" if d == nights + 1 else "full", items=[], hours=0.0, travel_minutes=0) for d in range(1, nights + 2)]
    free = [d for d in days if d["kind"] == "full"]
    pool = [inv.activity_by_id[i] for i in activity_ids if i in inv.activity_by_id]
    requested = set(req.activity_ids)
    pool.sort(key=lambda a: (a["id"] not in requested, -a["rating"]))
    overflow = []
    for day in free:
        if not pool:
            break
        cur = pool.pop(0)
        day["items"].append(cur); day["hours"] += cur["duration_hours"]
        while pool and len(day["items"]) < cap:  # add nearest remaining activity
            last = day["items"][-1]
            nxt = min(pool, key=lambda a: haversine_km(last["latitude"], last["longitude"], a["latitude"], a["longitude"]))
            km = haversine_km(last["latitude"], last["longitude"], nxt["latitude"], nxt["longitude"]); tmin = round(km / spd * 60)
            if day["hours"] + nxt["duration_hours"] + (day["travel_minutes"] + tmin) / 60 > hmax or km > 40:
                break
            pool.remove(nxt); day["items"].append(nxt); day["hours"] += nxt["duration_hours"]; day["travel_minutes"] += tmin
    overflow = [a["name"] for a in pool]
    for d in days:
        d["hours"] = round(d["hours"], 1); d["items"] = [dict(id=a["id"], name=a["name"], area=a["area"], hours=a["duration_hours"]) for a in d["items"]]
    return dict(days=days, overflow=overflow)


def itinerary_conflicts(it: dict, style: str) -> list[str]:
    """Check each day against the style cap/hours (no overlap by construction: one block per activity)."""
    cap, hmax = RANKING["activities_per_day"][style], RANKING["hours_per_day"][style]
    out = []
    for d in it["days"]:
        if len(d["items"]) > cap:
            out.append(f"Day {d['day']} has {len(d['items'])} activities (max {cap} for {style})")
        if d["hours"] + d["travel_minutes"] / 60 > hmax + 1e-9:
            out.append(f"Day {d['day']} is overloaded ({d['hours']}h)")
    out += [f"Could not schedule: {n}" for n in it["overflow"]]
    return out
