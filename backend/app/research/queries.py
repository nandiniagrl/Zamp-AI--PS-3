"""Search query builders for each research branch. Small, bounded query counts keep free credits safe."""
from dataclasses import dataclass
from datetime import date

from app.models import Conflict, ProspectInput


@dataclass(frozen=True)
class QuerySpec:
    query: str
    topic: str = "general"  # "general" | "news"
    time_range: str | None = None  # "day" | "week" | "month" | "year"
    max_results: int = 5


_ROLE_AREAS = {
    "sales": "sales", "revenue": "sales", "marketing": "marketing", "growth": "marketing",
    "cto": "engineering", "engineer": "engineering", "technology": "engineering", "data": "data",
    "cfo": "finance", "finance": "finance", "operations": "operations", "coo": "operations",
    "people": "HR", "hr": "HR", "talent": "HR", "product": "product",
}


def role_area(title: str) -> str:
    t = title.lower()
    return next((area for kw, area in _ROLE_AREAS.items() if kw in t), "")


def person_queries(p: ProspectInput) -> list[QuerySpec]:
    return [
        QuerySpec(f'"{p.name}" {p.company} interview OR podcast OR keynote OR said', time_range="year"),
        QuerySpec(f'"{p.name}" {p.company} {p.title}', topic="news", time_range="year"),
    ]


def company_queries(p: ProspectInput) -> list[QuerySpec]:
    return [
        QuerySpec(f"{p.company} announces launch OR partnership OR expansion", topic="news", time_range="year"),
        QuerySpec(f"{p.company} funding OR acquisition OR strategy {date.today().year}", topic="news", time_range="year"),
    ]


def hiring_queries(p: ProspectInput) -> list[QuerySpec]:
    area = role_area(p.title)
    return [QuerySpec(" ".join(x for x in (p.company, "hiring", area, "jobs careers") if x), time_range="month")]


def broadened_queries(p: ProspectInput, user_context: str | None = None) -> list[QuerySpec]:
    specs = [
        QuerySpec(f"{p.company} company overview products customers"),
        QuerySpec(f"{p.company} priorities OR initiatives OR growth {date.today().year}", topic="news", time_range="year"),
    ]
    if user_context:
        specs.append(QuerySpec(f"{p.company} {user_context.strip()[:150]}"))
    return specs


def targeted_queries(p: ProspectInput, conflict: Conflict) -> list[QuerySpec]:
    values = " OR ".join(conflict.values[:2])
    if conflict.claim_type in ("person_role", "employer"):
        return [QuerySpec(f'"{p.name}" {p.company} {conflict.key} {values}', max_results=6)]
    return [QuerySpec(f"{p.company} {conflict.key} {values}", topic="news", max_results=6)]
