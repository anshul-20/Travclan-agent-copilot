"""Supplier health score (0-100) and inventory-risk warnings."""
from app.config.settings import RANKING


def supplier_health(s: dict) -> int:
    """Weighted blend of confirmation, response time, cancellation, availability, complaints, price competitiveness."""
    score = (.35 * s["confirmation_rate"] + .20 * (1 - min(s["response_time_h"], 48) / 48) + .20 * (1 - min(s["cancellation_rate"] / .15, 1))
             + .10 * s["availability_rate"] + .10 * (1 - min(s["complaints_per_1k"] / 10, 1)) + .05 * s["price_competitiveness"])
    return int(round(100 * max(0.0, min(1.0, score))))


def supplier_risks(s: dict) -> list[str]:
    """Human-readable warnings derived from actual metrics (never invented)."""
    r, w = RANKING["supplier_risk"], []
    if s["confirmation_rate"] < r["min_confirmation"]:
        w.append(f"Supplier confirmation rate is {s['confirmation_rate']:.0%}")
    if s["cancellation_rate"] > r["max_cancellation"]:
        w.append(f"Supplier cancellation rate is {s['cancellation_rate']:.0%}")
    if s["response_time_h"] > r["max_response_h"]:
        w.append(f"Slow supplier response ({s['response_time_h']:.0f}h)")
    if s["price_volatility"] > .2:
        w.append("High price volatility")
    return w
