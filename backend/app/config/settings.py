"""Central configuration: environment settings and ranking/business-rule config."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/processed/copilot.db"
    embedding_backend: str = "auto"  # auto | st | hash
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_provider: str = "none"
    llm_api_key: str = ""
    require_auth: bool = False
    api_key: str = "change-me"
    data_seed: int = 42
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


# All ranking / business knobs live here, not scattered through the code.
RANKING = {
    "weights": {"sem": 0.30, "budget": 0.20, "rating": 0.15, "avail": 0.10,
                "pref": 0.10, "supplier": 0.05, "loc": 0.05, "biz": 0.05},
    "mmr_lambda": 0.7,
    "objective": "balanced",  # customer | balanced | margin
    "biz_weight": {"customer": 0.01, "balanced": 0.05, "margin": 0.12},
    "hotel_budget_share": 0.60,   # hard cap: hotel cost <= share * budget
    "tax_rate": 0.05,
    "activities_per_day": {"relaxed": 2, "balanced": 3, "packed": 4},
    "hours_per_day": {"relaxed": 6.0, "balanced": 8.0, "packed": 10.0},
    "travel_speed_kmh": 25.0,
    "supplier_risk": {"min_confirmation": 0.80, "max_cancellation": 0.08, "max_response_h": 30},
}
