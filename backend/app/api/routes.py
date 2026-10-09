"""REST API. Thin layer: validation + delegation to services."""
from __future__ import annotations
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from app.config.settings import get_settings
from app.schemas.schemas import ExtractRequest, ExtractionResult, ModifyRequest, RecommendRequest, Requirement, Trip
from app.services.requirement_extraction.extractor import extract_requirement
from app.services.supplier.health import supplier_risks

router = APIRouter(prefix="/api")


def auth(x_api_key: str | None = Header(default=None)):
    """Placeholder authentication: enforced only when REQUIRE_AUTH=true."""
    s = get_settings()
    if s.require_auth and x_api_key != s.api_key:
        raise HTTPException(401, "Invalid or missing API key")


def eng(request: Request):
    return request.app.state.engine


@router.post("/requirements/extract", response_model=ExtractionResult, dependencies=[Depends(auth)])
def extract(body: ExtractRequest, e=Depends(eng)):
    return extract_requirement(body.text, list(e.inv.destinations), e.inv.activities)


@router.post("/requirements/validate", dependencies=[Depends(auth)])
def validate_requirement(req: Requirement, e=Depends(eng)):
    issues = []
    if not req.destination:
        issues.append("destination is required")
    elif req.destination not in e.inv.destinations:
        issues.append(f"destination '{req.destination}' is not in the inventory")
    if req.nights is None:
        issues.append("duration is required")
    if req.budget is None:
        issues.append("budget is required for budget-fit ranking")
    hard = {k: v for k, v in dict(destination=req.destination, nights=req.nights, min_hotel_stars=req.hotel_star_rating, max_budget=req.budget, availability_required=True).items() if v is not None}
    return dict(valid=not any("required" in i or "inventory" in i for i in issues), issues=issues, hard_constraints=hard, soft_preferences=dict(style=req.travel_style, activities=req.activities, constraints=req.constraints))


@router.post("/recommendations", dependencies=[Depends(auth)])
def recommendations(body: RecommendRequest, e=Depends(eng)):
    if not body.requirement.destination or body.requirement.destination not in e.inv.destinations:
        raise HTTPException(422, "A supported destination is required")
    return e.recommend(body.requirement, body.mmr_lambda, body.objective, body.use_mmr, body.top_k)


@router.post("/recommendations/rerank", dependencies=[Depends(auth)])
def rerank(body: RecommendRequest, e=Depends(eng)):
    return recommendations(body, e)


@router.post("/trip/start", dependencies=[Depends(auth)])
def start_trip(body: Requirement, e=Depends(eng)):
    try:
        return e.start_trip(body)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.post("/itinerary/generate", dependencies=[Depends(auth)])
def itinerary(trip: Trip, e=Depends(eng)):
    return e.quote(trip)["itinerary"]


@router.post("/itinerary/optimize", dependencies=[Depends(auth)])
def itinerary_opt(trip: Trip, e=Depends(eng)):
    from app.services.itinerary.planner import select_activities
    trip = trip.model_copy(update={"activity_ids": select_activities(e.inv, trip.requirement, None)})
    return dict(trip=trip, itinerary=e.quote(trip)["itinerary"])


@router.post("/quote/generate", dependencies=[Depends(auth)])
def quote_generate(trip: Trip, e=Depends(eng)):
    if trip.hotel_id not in e.inv.hotel_by_id:
        raise HTTPException(404, "Unknown hotel_id")
    return e.quote(trip)


@router.post("/quote/validate", dependencies=[Depends(auth)])
def quote_validate(trip: Trip, e=Depends(eng)):
    q = e.quote(trip)
    return dict(ready_to_send=q["ready_to_send"], validation=q["validation"])


@router.post("/trip/modify", dependencies=[Depends(auth)])
def modify(body: ModifyRequest, e=Depends(eng)):
    return e.modify(body.trip, body.command)


@router.get("/hotels", dependencies=[Depends(auth)])
def hotels(destination: str | None = None, min_stars: int | None = None, limit: int = Query(50, le=500), e=Depends(eng)):
    r = [h for h in e.inv.hotels if (not destination or h["destination"] == destination) and (not min_stars or h["star_rating"] >= min_stars)]
    return r[:limit]


@router.get("/activities", dependencies=[Depends(auth)])
def activities(destination: str | None = None, limit: int = Query(50, le=500), e=Depends(eng)):
    return [a for a in e.inv.activities if not destination or a["destination"] == destination][:limit]


@router.get("/destinations", dependencies=[Depends(auth)])
def destinations(e=Depends(eng)):
    return list(e.inv.destinations.values())


@router.get("/suppliers", dependencies=[Depends(auth)])
def suppliers(e=Depends(eng)):
    return sorted(e.inv.suppliers.values(), key=lambda s: s["health"])


@router.get("/suppliers/{sid}/health", dependencies=[Depends(auth)])
def supplier_health_ep(sid: str, e=Depends(eng)):
    s = e.inv.suppliers.get(sid)
    if not s:
        raise HTTPException(404, "Unknown supplier")
    return dict(id=sid, health=s["health"], metrics={k: v for k, v in s.items() if k not in ("id", "name", "health")}, risks=supplier_risks(s))
