"""Generate synthetic data to data/processed/*.json (deterministic)."""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
from app.utils.datagen import generate
from app.config.settings import get_settings

if __name__ == "__main__":
    out = pathlib.Path(__file__).resolve().parents[1] / "data" / "processed"; out.mkdir(parents=True, exist_ok=True)
    data = generate(get_settings().data_seed)
    for k, v in data.items():
        (out / f"{k}.json").write_text(json.dumps(v))
        print(f"{k:13s} {len(v):5d} rows")
