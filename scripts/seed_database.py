"""Create tables and load synthetic data into the configured database (SQLite by default, PostgreSQL in docker)."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.models import db
from app.models.session import get_engine, get_session
from app.utils.datagen import generate
from app.config.settings import get_settings

ORDER = [("suppliers", db.Supplier), ("destinations", db.Destination), ("hotels", db.Hotel), ("activities", db.Activity), ("transfers", db.Transfer), ("customers", db.Customer)]


def seed(reset: bool = True) -> dict:
    eng = get_engine()
    if reset:
        db.Base.metadata.drop_all(eng)
    db.Base.metadata.create_all(eng)
    data = generate(get_settings().data_seed)
    with get_session() as s:
        for key, model in ORDER:
            s.add_all([model(**r) for r in data[key]])
        s.commit()
    return {k: len(v) for k, v in data.items()}


if __name__ == "__main__":
    (ROOT / "data" / "processed").mkdir(parents=True, exist_ok=True)
    print(seed())
