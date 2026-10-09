import numpy as np, pytest
from app.config.settings import RANKING
from app.embeddings.embedder import Embedder, VectorIndex
from app.schemas.schemas import Requirement, Travelers
from app.services.itinerary.planner import build_itinerary, itinerary_conflicts, select_activities
from app.services.mmr.mmr import avg_pairwise_similarity, mmr_select
from app.services.pricing.engine import price_trip
from app.services.ranking.ranker import hard_filter_hotels
from app.services.requirement_extraction.extractor import classify_intent, extract_requirement, parse_budget, parse_duration, parse_month
from app.services.supplier.health import supplier_health, supplier_risks
from app.utils.datagen import generate


# ---- data ----
def test_data_is_deterministic():
    a, b = generate(1, n_customers=5), generate(1, n_customers=5)
    assert a["hotels"] == b["hotels"] and a["suppliers"] == b["suppliers"]

def test_data_volumes(data):
    assert len(data["hotels"]) >= 500 and len(data["activities"]) >= 500 and len(data["suppliers"]) >= 100 and len(data["customers"]) >= 1000

def test_price_correlates_with_star(data):
    d = [h for h in data["hotels"] if h["destination"] == "Dubai"]
    avg = lambda s: np.mean([h["base_price_per_night"] for h in d if h["star_rating"] == s])
    assert avg(3) < avg(4) < avg(5)

# ---- extraction ----
@pytest.mark.parametrize("t,v", [("budget 1.2 lakh", 120000), ("₹1.2L", 120000), ("around 120k", 120000), ("₹1,20,000", 120000), ("under Rs. 95000", 95000)])
def test_budget_parser(t, v):
    assert parse_budget(t)[0] == v

def test_budget_missing():
    assert parse_budget("no money talk")[0] is None

def test_duration_parser():
    assert parse_duration("5 nights")[:2] == (6, 5) and parse_duration("6 days")[:2] == (6, 5)

def test_month_parser():
    assert parse_month("travelling in November") == "November" and parse_month("sometime soon") is None

def test_demo_extraction(demo_req):
    r = demo_req.requirement
    assert (r.destination, r.nights, r.budget, r.hotel_star_rating, r.travel_style) == ("Dubai", 5, 120000, 4, "relaxed") and r.travelers.adults == 2
    assert len(r.activity_ids) == 2 and demo_req.intent == "SEARCH_DESTINATION"

def test_vague_request_asks_clarification(inv):
    e = extract_requirement("Plan a trip to Europe.", list(inv.destinations))
    assert "destination" in e.missing and any("countries/cities" in q for q in e.clarifications)

def test_intents():
    assert classify_intent("Add a Marina cruise") == "ADD_ACTIVITY" and classify_intent("Remove the Dubai Frame") == "REMOVE_ACTIVITY"
    assert classify_intent("Show me three alternatives") == "COMPARE_OPTIONS" and classify_intent("Replace the hotel with something cheaper") == "CHANGE_HOTEL"

# ---- retrieval / ranking ----
def test_semantic_matching_without_keywords():
    e = Embedder("hash"); v = e.embed_text(["quiet romantic hotel close to the beach", "peaceful beachfront property ideal for couples", "central business hotel near metro and shopping"])
    assert v[0] @ v[1] > v[0] @ v[2] + .1

def test_vector_index_returns_self_first():
    e = Embedder("hash"); v = e.embed_text(["a beach resort", "city hotel", "spa retreat"]); ix = VectorIndex(v, ["a", "b", "c"])
    assert ix.search_similar(v[1], 1)[0][0] == "b"

def test_hard_filters(inv, demo_req):
    r = demo_req.requirement; ok, rej = hard_filter_hotels(inv.hotels, r)
    assert ok and all(h["destination"] == "Dubai" and h["availability"] and h["star_rating"] >= 4 for h in ok)

def test_recommendations_respect_hard_constraints(engine, demo_req):
    res = engine.recommend(demo_req.requirement)
    assert res["items"] and all(inv_ok(engine, i) for i in res["items"])

def inv_ok(engine, item):
    h = engine.inv.hotel_by_id[item["hotel_id"]]; return h["availability"] and h["star_rating"] >= 4 and h["destination"] == "Dubai"

def test_explanations_are_attribute_based(engine, demo_req):
    for i in engine.recommend(demo_req.requirement)["items"]:
        assert "4-star" in i["explanation"] and i["area"] in i["explanation"]

def test_mmr_increases_diversity(engine, demo_req):
    r = demo_req.requirement
    div = lambda res: 1 - avg_pairwise_similarity(np.stack([engine.retriever.vec[i["hotel_id"]] for i in res["items"]]))
    assert div(engine.recommend(r, use_mmr=True)) >= div(engine.recommend(r, use_mmr=False))

def test_mmr_lambda_one_is_pure_relevance():
    rel = np.array([.9, .8, .7, .1]); vec = np.eye(4, dtype="float32")
    assert [s["index"] for s in mmr_select(rel, vec, 3, 1.0)] == [0, 1, 2]

def test_mmr_penalises_duplicates():
    rel = np.array([.9, .89, .5]); vec = np.array([[1, 0], [1, 0], [0, 1]], dtype="float32")
    assert [s["index"] for s in mmr_select(rel, vec, 2, .5)] == [0, 2]

def test_weights_sum_to_one():
    assert abs(sum(RANKING["weights"].values()) - 1) < 1e-9

# ---- pricing / margin ----
def test_pricing_arithmetic(inv, demo_req):
    r = demo_req.requirement; h = next(x for x in inv.hotels if x["destination"] == "Dubai" and x["star_rating"] == 4)
    p = price_trip(inv, r, h, r.activity_ids, "private", markup=.12)
    assert p["supplier_cost"] == pytest.approx(p["hotel_cost"] + p["activity_cost"] + p["transfer_cost"], abs=.02)
    assert p["total"] == pytest.approx((p["supplier_cost"] * 1.12) * 1.05, abs=.05) and p["gross_margin"] == pytest.approx(p["supplier_cost"] * .12, abs=.02)
    assert p["margin_pct"] == pytest.approx(.12 / 1.12 * 100, abs=.05)

def test_discount_reduces_margin_not_cost(inv, demo_req):
    r = demo_req.requirement; h = inv.hotels[0]; r2 = r.model_copy(update={"destination": h["destination"], "transfers_requested": False})
    a, b = price_trip(inv, r2, h, [], markup=.1), price_trip(inv, r2, h, [], markup=.1, discount=1000)
    assert b["supplier_cost"] == a["supplier_cost"] and b["gross_margin"] == pytest.approx(a["gross_margin"] - 1000, abs=.02)

# ---- supplier ----
def test_supplier_health_monotonic():
    good = dict(confirmation_rate=.97, response_time_h=4, cancellation_rate=.01, availability_rate=.95, complaints_per_1k=1, price_competitiveness=.8, price_volatility=.05)
    bad = dict(good, confirmation_rate=.65, response_time_h=40, cancellation_rate=.12, complaints_per_1k=8)
    assert supplier_health(good) > supplier_health(bad) + 25 and supplier_risks(bad) and not supplier_risks(good)

# ---- itinerary ----
def test_itinerary_respects_style_cap(engine, demo_req):
    r = demo_req.requirement; t = engine.start_trip(r); it = build_itinerary(engine.inv, r, engine.inv.hotel_by_id[t.hotel_id], t.activity_ids)
    assert not itinerary_conflicts(it, "relaxed") and all(len(d["items"]) <= 2 for d in it["days"]) and len(it["days"]) == 6
    assert it["days"][0]["kind"] == "arrival" and it["days"][-1]["kind"] == "departure"

def test_requested_activities_are_kept(engine, demo_req):
    r = demo_req.requirement; assert set(r.activity_ids) <= set(select_activities(engine.inv, r))

# ---- validation / quote / modify ----
def test_quote_passes_for_demo(engine, demo_req):
    q = engine.quote(engine.start_trip(demo_req.requirement)); assert q["ready_to_send"] and q["pricing"]["total"] <= 120000

def test_over_budget_is_flagged_not_hidden(engine, demo_req):
    r = demo_req.requirement.model_copy(update={"budget": 20000}); h = next(x for x in engine.inv.hotels if x["destination"] == "Dubai" and x["star_rating"] == 5)
    from app.schemas.schemas import Trip
    q = engine.quote(Trip(requirement=r, hotel_id=h["id"], activity_ids=r.activity_ids))
    assert not q["ready_to_send"] and any(v["check"] == "Budget" and v["status"] == "fail" for v in q["validation"]) and q["budget_optimizer"]

def test_modify_add_remove_markup(engine, demo_req):
    t = engine.start_trip(demo_req.requirement)
    add = engine.modify(t, "Add a marina cruise"); assert add["changed"] and add["delta"]["price"] > 0
    rm = engine.modify(t, "Remove the Burj Khalifa"); assert rm["changed"] and rm["delta"]["price"] < 0
    mk = engine.modify(t, "set markup 20%"); assert mk["after"]["pricing"]["markup_rate"] == .2

def test_modify_unknown_command_changes_nothing(engine, demo_req):
    assert engine.modify(engine.start_trip(demo_req.requirement), "dance")["changed"] is False

def test_unavailable_hotel_fails_validation(engine, demo_req):
    from app.schemas.schemas import Trip
    h = next(x for x in engine.inv.hotels if not x["availability"] and x["destination"] == "Dubai")
    q = engine.quote(Trip(requirement=demo_req.requirement, hotel_id=h["id"], activity_ids=[]))
    assert any(v["check"] == "Hotel availability" and v["status"] == "fail" for v in q["validation"])
