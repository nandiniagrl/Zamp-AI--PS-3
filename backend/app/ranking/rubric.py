"""Weighted scoring rubric. Totals are computed deterministically in Python.

Credibility and recency come from source metadata (not the LLM); the LLM scores only relevance,
specificity and usefulness. Scores are heuristic, NOT calibrated probabilities.
"""
from datetime import date

from app.models import DimensionScores, Evidence
from app.utils.dates import age_days

WEIGHTS = {
    "business_relevance": 0.30,
    "specificity": 0.25,
    "credibility": 0.20,
    "recency": 0.15,
    "outreach_usefulness": 0.10,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "rubric weights must sum to 1"

MIN_HOOK_SCORE = 40.0
DISCLAIMER = "Scores are a weighted heuristic rubric (0–100), not calibrated probabilities."


def credibility_score(e: Evidence) -> float:
    base = {"high": 9, "medium": 6, "low": 3}[e.credibility]
    return float(min(10, base + (1 if e.corroborating_urls else 0)))


def recency_score(e: Evidence, today: date | None = None) -> float:
    days = age_days(e.event_date, today) if e.event_date else None
    if days is None:
        days = age_days(e.publication_date, today)
    if days is None:
        return 3.0  # unknown date: neutral-low, never rewarded
    for limit, score in ((30, 10), (90, 8), (180, 6), (365, 4)):
        if days <= limit:
            return float(score)
    return 2.0


def total(scores: DimensionScores) -> float:
    return round(10 * sum(getattr(scores, k) * w for k, w in WEIGHTS.items()), 1)
