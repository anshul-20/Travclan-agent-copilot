"""Run the main demo flow against the engine and print results (no server needed)."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
from app.main import build_engine
from app.services.requirement_extraction.extractor import extract_requirement

TXT = "I have a couple travelling to Dubai for 5 nights in November. Their budget is around ₹1.2 lakh. They want a 4-star hotel, desert safari, Burj Khalifa and airport transfers. They prefer a relaxed trip."
e = build_engine(); ex = extract_requirement(TXT, list(e.inv.destinations), e.inv.activities); r = ex.requirement
print("EXTRACTED:", r.destination, r.nights, "nights", r.budget, r.hotel_star_rating, "star", r.travel_style, r.activities, "| confidence", ex.overall_confidence)
for i in e.recommend(r)["items"]:
    print(f"  {i['category']:28s} {i['name']:28s} {i['star_rating']}★ ₹{i['estimated_total']:>10,.0f} margin ₹{i['estimated_margin']:,.0f} score {i['scores']['final']}")
t = e.start_trip(r); q = e.quote(t); p = q["pricing"]
print(f"QUOTE: ₹{p['total']:,.0f} (cost ₹{p['supplier_cost']:,.0f}, margin ₹{p['gross_margin']:,.0f} = {p['margin_pct']}%) ready_to_send={q['ready_to_send']}")
for cmd in ["Add a marina cruise", "Remove the Burj Khalifa", "Make the itinerary more relaxed"]:
    m = e.modify(t, cmd); print(f"  '{cmd}' -> {m['note']} | Δprice {m.get('delta', {}).get('price')}")
