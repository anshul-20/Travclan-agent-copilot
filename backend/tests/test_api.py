import pytest
from fastapi.testclient import TestClient

TXT = "Couple, Dubai, 5 nights in November, budget 1.2 lakh, 4-star hotel, desert safari, relaxed"

@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c

def test_health(client):
    assert client.get("/health").json()["data"] == "synthetic"

def test_full_flow(client):
    ex = client.post("/api/requirements/extract", json={"text": TXT}).json(); req = ex["requirement"]
    assert req["destination"] == "Dubai" and client.post("/api/requirements/validate", json=req).json()["valid"]
    rec = client.post("/api/recommendations", json={"requirement": req}).json(); assert rec["items"] and rec["items"][0]["scores"]["final"] > 0
    trip = client.post("/api/trip/start", json=req).json()
    q = client.post("/api/quote/generate", json=trip).json(); assert q["pricing"]["total"] > 0 and q["validation"]
    m = client.post("/api/trip/modify", json={"trip": trip, "command": "add a marina cruise"}).json(); assert m["changed"]

def test_rejects_bad_input(client):
    assert client.post("/api/requirements/extract", json={"text": ""}).status_code == 422
    assert client.post("/api/recommendations", json={"requirement": {"nights": 3}}).status_code == 422

def test_inventory_endpoints(client):
    assert len(client.get("/api/destinations").json()) == 17 and client.get("/api/hotels?destination=Dubai&limit=3").json()
    sid = client.get("/api/suppliers").json()[0]["id"]; assert "health" in client.get(f"/api/suppliers/{sid}/health").json()
    assert client.get("/api/suppliers/NOPE/health").status_code == 404
