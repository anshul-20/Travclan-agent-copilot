"""SQLAlchemy models (synthetic inventory + core workflow tables)."""
from datetime import datetime
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    confirmation_rate: Mapped[float] = mapped_column(Float)
    response_time_h: Mapped[float] = mapped_column(Float)
    cancellation_rate: Mapped[float] = mapped_column(Float)
    availability_rate: Mapped[float] = mapped_column(Float)
    complaints_per_1k: Mapped[float] = mapped_column(Float)
    price_competitiveness: Mapped[float] = mapped_column(Float)
    price_volatility: Mapped[float] = mapped_column(Float)


class Destination(Base):
    __tablename__ = "destinations"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    name: Mapped[str] = mapped_column(String(60), index=True)
    country: Mapped[str] = mapped_column(String(60))
    region: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    best_months: Mapped[list] = mapped_column(JSON)
    average_duration: Mapped[int] = mapped_column(Integer)
    budget_category: Mapped[str] = mapped_column(String(20))
    scores: Mapped[dict] = mapped_column(JSON)
    visa_note: Mapped[str] = mapped_column(String(120))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    price_multiplier: Mapped[float] = mapped_column(Float)


class Hotel(Base):
    __tablename__ = "hotels"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    destination: Mapped[str] = mapped_column(String(60), index=True)
    area: Mapped[str] = mapped_column(String(60))
    star_rating: Mapped[int] = mapped_column(Integer)
    hotel_type: Mapped[str] = mapped_column(String(20))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)
    amenities: Mapped[list] = mapped_column(JSON)
    room_types: Mapped[list] = mapped_column(JSON)
    base_price_per_night: Mapped[float] = mapped_column(Float)
    meal_plan: Mapped[str] = mapped_column(String(30))
    rating: Mapped[float] = mapped_column(Float)
    review_count: Mapped[int] = mapped_column(Integer)
    family_friendly: Mapped[bool] = mapped_column(Boolean)
    couple_friendly: Mapped[bool] = mapped_column(Boolean)
    luxury_score: Mapped[float] = mapped_column(Float)
    budget_score: Mapped[float] = mapped_column(Float)
    location_score: Mapped[float] = mapped_column(Float)
    margin_pct: Mapped[float] = mapped_column(Float)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"))
    availability: Mapped[bool] = mapped_column(Boolean)
    cancellation_policy: Mapped[str] = mapped_column(String(40))


class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    destination: Mapped[str] = mapped_column(String(60), index=True)
    area: Mapped[str] = mapped_column(String(60))
    category: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    keywords: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    duration_hours: Mapped[float] = mapped_column(Float)
    price_per_person: Mapped[float] = mapped_column(Float)
    rating: Mapped[float] = mapped_column(Float)
    review_count: Mapped[int] = mapped_column(Integer)
    family_friendly: Mapped[bool] = mapped_column(Boolean)
    couple_friendly: Mapped[bool] = mapped_column(Boolean)
    adventure_score: Mapped[float] = mapped_column(Float)
    relaxation_score: Mapped[float] = mapped_column(Float)
    culture_score: Mapped[float] = mapped_column(Float)
    popularity_score: Mapped[float] = mapped_column(Float)
    availability: Mapped[bool] = mapped_column(Boolean)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"))


class Transfer(Base):
    __tablename__ = "transfers"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    destination: Mapped[str] = mapped_column(String(60), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    vehicle_type: Mapped[str] = mapped_column(String(30))
    capacity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    per_person: Mapped[bool] = mapped_column(Boolean)
    duration_min: Mapped[int] = mapped_column(Integer)
    availability: Mapped[bool] = mapped_column(Boolean)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"))


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(40))
    city: Mapped[str] = mapped_column(String(40))
    traveler_type: Mapped[str] = mapped_column(String(20))
    preferred_budget: Mapped[float] = mapped_column(Float)
    preferred_destinations: Mapped[list] = mapped_column(JSON)
    preferred_travel_style: Mapped[str] = mapped_column(String(20))
    preferred_activities: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Quote(Base):
    __tablename__ = "quotes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    trip_id: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    total_price: Mapped[float] = mapped_column(Float)
    gross_margin: Mapped[float] = mapped_column(Float)
    change_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(40))
    item_id: Mapped[str] = mapped_column(String(20))
    useful: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
