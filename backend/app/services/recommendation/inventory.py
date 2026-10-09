"""Data layer: loads inventory from the DB into in-memory indexes (DB is the source of truth)."""
from __future__ import annotations
from dataclasses import dataclass, field
from sqlalchemy import select
from app.models import db


def _row(o) -> dict:
    return {c.name: getattr(o, c.name) for c in o.__table__.columns}


@dataclass
class Inventory:
    hotels: list[dict]
    activities: list[dict]
    transfers: list[dict]
    suppliers: dict[str, dict]
    destinations: dict[str, dict]
    hotel_by_id: dict[str, dict] = field(default_factory=dict)
    activity_by_id: dict[str, dict] = field(default_factory=dict)

    def __post_init__(self):
        self.hotel_by_id = {h["id"]: h for h in self.hotels}
        self.activity_by_id = {a["id"]: a for a in self.activities}

    def activities_in(self, dest: str) -> list[dict]:
        return [a for a in self.activities if a["destination"] == dest]

    @classmethod
    def from_session(cls, s) -> "Inventory":
        from app.services.supplier.health import supplier_health
        sup = {x.id: _row(x) for x in s.scalars(select(db.Supplier))}
        for v in sup.values():
            v["health"] = supplier_health(v)
        return cls(hotels=[_row(x) for x in s.scalars(select(db.Hotel))], activities=[_row(x) for x in s.scalars(select(db.Activity))],
                   transfers=[_row(x) for x in s.scalars(select(db.Transfer))], suppliers=sup, destinations={x.name: _row(x) for x in s.scalars(select(db.Destination))})
