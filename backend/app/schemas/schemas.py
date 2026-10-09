"""Pydantic schemas (API + domain)."""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field

Style = Literal["relaxed", "balanced", "packed"]


class Travelers(BaseModel):
    adults: int = Field(2, ge=1, le=20)
    children: int = Field(0, ge=0, le=20)


class Requirement(BaseModel):
    destination: Optional[str] = None
    travelers: Travelers = Travelers()
    duration_days: Optional[int] = Field(None, ge=1, le=60)
    nights: Optional[int] = Field(None, ge=0, le=60)
    budget: Optional[float] = Field(None, gt=0)
    currency: str = "INR"
    hotel_star_rating: Optional[int] = Field(None, ge=1, le=5)
    activities: list[str] = []          # human-readable names
    activity_ids: list[str] = []        # resolved against inventory
    travel_style: Style = "balanced"
    transfers_requested: bool = False
    month: Optional[str] = None
    constraints: list[str] = []
    raw_text: str = ""


class ExtractionResult(BaseModel):
    requirement: Requirement
    confidence: dict[str, float]
    overall_confidence: float
    missing: list[str]
    clarifications: list[str]
    intent: str


class ExtractRequest(BaseModel):
    text: str = Field(min_length=3, max_length=4000)


class RecommendRequest(BaseModel):
    requirement: Requirement
    mmr_lambda: Optional[float] = Field(None, ge=0, le=1)
    objective: Optional[Literal["customer", "balanced", "margin"]] = None
    use_mmr: bool = True
    top_k: int = Field(5, ge=1, le=10)


class Trip(BaseModel):
    requirement: Requirement
    hotel_id: str
    activity_ids: list[str] = []
    transfer_type: Literal["private", "shared"] = "private"
    markup: Optional[float] = Field(None, ge=0, le=1)
    discount: float = Field(0, ge=0)


class ModifyRequest(BaseModel):
    trip: Trip
    command: str = Field(min_length=2, max_length=500)
