import sys, pathlib, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import tempfile
os.environ["EMBEDDING_BACKEND"] = "hash"
os.environ["DATABASE_URL"] = "sqlite:////" + tempfile.mkdtemp().lstrip("/") + "/test.db"  # empty DB: exercises auto-seed
import pytest
from app.embeddings.embedder import Embedder
from app.models import db
from app.services.recommendation.engine import CopilotEngine
from app.services.recommendation.inventory import Inventory
from app.services.supplier.health import supplier_health
from app.utils.datagen import generate


@pytest.fixture(scope="session")
def data():
    return generate(42)


@pytest.fixture(scope="session")
def inv(data):
    sup = {s["id"]: dict(s, health=supplier_health(s)) for s in data["suppliers"]}
    ren = lambda h: {**{k: v for k, v in h.items() if k != "star_rating"}, "star_rating": h["star_rating"]}
    return Inventory(hotels=data["hotels"], activities=data["activities"], transfers=data["transfers"], suppliers=sup, destinations={d["name"]: d for d in data["destinations"]})


@pytest.fixture(scope="session")
def engine(inv):
    return CopilotEngine(inv, Embedder("hash"))


@pytest.fixture(scope="session")
def demo_req(inv):
    from app.services.requirement_extraction.extractor import extract_requirement
    t = "I have a couple travelling to Dubai for 5 nights in November. Their budget is around ₹1.2 lakh. They want a 4-star hotel, desert safari, Burj Khalifa and airport transfers. They prefer a relaxed trip."
    return extract_requirement(t, list(inv.destinations), inv.activities)
