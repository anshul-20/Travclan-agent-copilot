"""Requirement extraction: deterministic parsers (budget/date/nights/...) + intent classification.
An LLM can be layered on top for messy text, but every value is validated through Pydantic and rule parsers."""
from __future__ import annotations
import re
from app.schemas.schemas import ExtractionResult, Requirement, Travelers

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
ALIASES = {"uae": "Dubai", "emirates": "Dubai", "krabi": "Phuket", "kuala lumpur": "Malaysia", "hanoi": "Vietnam", "tokyo": "Japan", "sydney": "Australia", "colombo": "Sri Lanka", "kathmandu": "Nepal", "swiss": "Switzerland"}
INTENTS = [("CHANGE_BUDGET", r"(change|increase|reduce|lower|raise|set|update).{0,15}budget|budget.{0,15}(change|increase|reduce)"), ("MODIFY_ITINERARY", r"(more|less) (relaxed|packed)|too packed|reorder|reschedule"),
 ("CHANGE_HOTEL", r"(replace|change|swap).*hotel|cheaper hotel|better value"), ("ADD_ACTIVITY", r"^\s*(add|include)\b"), ("REMOVE_ACTIVITY", r"^\s*(remove|drop|delete)\b"),
 ("CHANGE_DATES", r"(change|shift|move).*(date|month)"), ("COMPARE_OPTIONS", r"alternative|compare|options|tradeoff"), ("VALIDATE_QUOTE", r"validate|check the quote"),
 ("GENERATE_QUOTE", r"\bquote\b|quotation"), ("BUILD_ITINERARY", r"itinerary|day.?wise|plan the days"), ("SEARCH_HOTEL", r"\bhotels?\b.*(find|show|suggest|search)|(find|show|suggest|search).*\bhotels?\b"),
 ("SEARCH_ACTIVITY", r"(find|show|suggest|search).*(activit|things to do|tour)"), ("ASK_TRAVEL_QUESTION", r"\?\s*$|^(what|when|how|is|are|do)\b"), ("SEARCH_DESTINATION", r"trip|travel|holiday|vacation|package|visit|\bnights?\b|\bdays?\b")]


def parse_budget(text: str) -> tuple[float | None, float]:
    """Parse INR amounts: '1.2 lakh', '₹1.2L', '120k', '₹1,20,000', '120000'. Returns (value, confidence)."""
    t = text.lower().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?|l\b)", t)
    if m:
        return round(float(m.group(1)) * 100000), .95
    m = re.search(r"(\d+(?:\.\d+)?)\s*k\b", t)
    if m:
        return round(float(m.group(1)) * 1000), .9
    m = re.search(r"(?:₹|rs\.?|inr)\s*(\d{4,9})|(?:budget|under|around|within)\D{0,12}(\d{5,9})", t)
    if m:
        return float(m.group(1) or m.group(2)), .9
    return None, 0.0


def parse_month(text: str) -> str | None:
    t = text.lower()
    for m in MONTHS:
        if re.search(rf"\b{m}\b", t) or re.search(rf"\b{m[:3]}\b", t):
            return m.capitalize()
    return None


def parse_duration(text: str) -> tuple[int | None, int | None, float]:
    """Return (days, nights, confidence). '5 nights' -> 6 days; '6 days' -> 5 nights."""
    t = text.lower()
    m = re.search(r"(\d+)\s*[- ]?nights?", t)
    if m:
        n = int(m.group(1)); return n + 1, n, .99
    m = re.search(r"(\d+)\s*[- ]?days?", t)
    if m:
        d = int(m.group(1)); return d, max(d - 1, 0), .9
    return None, None, 0.0


def classify_intent(text: str) -> str:
    t = text.lower()
    for name, pat in INTENTS:
        if re.search(pat, t):
            return name
    return "SEARCH_DESTINATION"


def find_destination(text: str, known: list[str]) -> str | None:
    t = text.lower()
    for k in sorted(known, key=len, reverse=True):
        if re.search(rf"\b{re.escape(k.lower())}\b", t):
            return k
    for a, d in ALIASES.items():
        if a in t and d in known:
            return d
    return None


def extract_requirement(text: str, destinations: list[str], activities: list[dict] | None = None) -> ExtractionResult:
    """Extract a validated Requirement with per-field confidence and clarification questions."""
    t, conf, cons = text.lower(), {}, []
    dest = find_destination(text, destinations)
    if dest:
        conf["destination"] = .99
    adults, children = 2, 0
    m = re.search(r"(\d+)\s*adults?", t)
    if m:
        adults, conf["travelers"] = int(m.group(1)), .98
    elif re.search(r"couple|honeymoon", t):
        adults, conf["travelers"] = 2, .95
    elif re.search(r"\bfamily\b", t):
        adults, conf["travelers"] = 2, .7
    elif re.search(r"\bsolo\b", t):
        adults, conf["travelers"] = 1, .9
    else:
        conf["travelers"] = .4  # defaulted, flagged for confirmation
    m = re.search(r"(\d+)\s*(?:kids?|children|child)", t)
    if m:
        children = int(m.group(1))
    elif re.search(r"\bfamily\b", t):
        children = 2
    days, nights, c = parse_duration(t)
    if c:
        conf["duration"] = c
    budget, c = parse_budget(text)
    if c:
        conf["budget"] = c
    m = re.search(r"(\d)\s*-?\s*star", t)
    star = int(m.group(1)) if m else None
    if star:
        conf["hotel_star_rating"] = .93
    style = "relaxed" if re.search(r"relax|not too packed|slow|laid.?back|don'?t want a packed", t) else "packed" if re.search(r"\bpacked\b|action|see everything", t) else "balanced"
    conf["travel_style"] = .5 if style == "balanced" else .87
    if re.search(r"not too expensive|cheap|affordable|within budget|under", t):
        cons.append("Stay within budget")
    if re.search(r"packed|long drives?", t) and re.search(r"(don'?t|not|no|avoid)", t):
        cons.append("Avoid packed itinerary" if "packed" in t else "Avoid long drives")
    month = parse_month(text)
    if month:
        conf["month"] = .95
    ids, names = [], []
    if dest and activities:
        for a in activities:
            if a["destination"] == dest and re.search(a["keywords"], t):
                ids.append(a["id"]); names.append(a["name"])
        if ids:
            conf["activities"] = .92
    req = Requirement(destination=dest, travelers=Travelers(adults=adults, children=children), duration_days=days, nights=nights, budget=budget, hotel_star_rating=star, activities=names,
                      activity_ids=ids, travel_style=style, transfers_requested=bool(re.search(r"transfer|pick-?up|airport", t)), month=month, constraints=cons, raw_text=text)
    missing, clar = [], []
    if not dest:
        missing.append("destination"); clar.append("Which countries/cities would you like to visit?")
    if nights is None:
        missing.append("duration"); clar.append("How many nights is the trip?")
    if budget is None:
        missing.append("budget"); clar.append("What is the approximate budget?")
    if conf["travelers"] < .5:
        clar.append("How many adults and children are travelling?")
    overall = round(sum(conf.values()) / len(conf), 3) if conf else 0.0
    return ExtractionResult(requirement=req, confidence=conf, overall_confidence=overall, missing=missing, clarifications=clar, intent=classify_intent(text))
