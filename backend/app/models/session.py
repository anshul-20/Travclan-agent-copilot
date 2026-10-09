"""DB engine/session factory. Relative SQLite paths resolve against the repo root, not the cwd."""
import pathlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config.settings import get_settings

ROOT = pathlib.Path(__file__).resolve().parents[3]
_engine = None


def resolve_url(url: str) -> str:
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        path = ROOT / url[len("sqlite:///"):]
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"
    return url


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(resolve_url(get_settings().database_url), future=True)
    return _engine


def get_session():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)()
