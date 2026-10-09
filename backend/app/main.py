"""FastAPI entrypoint. Run: uvicorn app.main:app --app-dir backend"""
import logging, time, uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect
from app.api.routes import router
from app.config.settings import get_settings
from app.embeddings.embedder import Embedder
from app.models.session import get_engine, get_session
from app.services.recommendation.engine import CopilotEngine
from app.services.recommendation.inventory import Inventory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("copilot")


def build_engine() -> CopilotEngine:
    s = get_settings()
    if not inspect(get_engine()).has_table("hotels"):
        log.info("Empty database: seeding synthetic data")
        import importlib.util, pathlib
        p = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "seed_database.py"
        spec = importlib.util.spec_from_file_location("seed_database", p); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); mod.seed()
    with get_session() as sess:
        inv = Inventory.from_session(sess)
    t = time.perf_counter(); emb = Embedder(s.embedding_backend, s.embedding_model); eng = CopilotEngine(inv, emb)
    log.info("engine ready: %d hotels, %d activities, embeddings=%s, index build %.0fms", len(inv.hotels), len(inv.activities), emb.backend, (time.perf_counter() - t) * 1000)
    return eng


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = build_engine()
    yield


app = FastAPI(title="Agent Copilot API (synthetic demo data)", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.middleware("http")
async def observe(request: Request, call_next):
    rid, t = uuid.uuid4().hex[:8], time.perf_counter()
    resp = await call_next(request)  # request bodies are never logged (may contain customer text)
    log.info("request_id=%s %s %s status=%s latency_ms=%.1f", rid, request.method, request.url.path, resp.status_code, (time.perf_counter() - t) * 1000)
    resp.headers["X-Request-ID"] = rid
    return resp


@app.get("/health")
def health():
    return {"status": "ok", "embedding_backend": app.state.engine.emb.backend, "data": "synthetic"}
