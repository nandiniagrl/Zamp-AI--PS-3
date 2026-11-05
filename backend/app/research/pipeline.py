"""Runs research branches through Tavily and returns sanitised, deduplicated ResearchRecords."""
import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from rapidfuzz import fuzz

from app.models import ProspectInput, ResearchRecord
from app.research import queries
from app.research.queries import QuerySpec
from app.safety.sanitize import sanitize_untrusted
from app.tools import tavily_client  # call via module so tests can swap search()

BRANCH_QUERIES = {
    "person": queries.person_queries,
    "company": queries.company_queries,
    "hiring": queries.hiring_queries,
}
_TRACKING_PREFIXES = ("utm_", "ref", "fbclid", "gclid", "mc_")


@dataclass
class BranchResult:
    records: list[ResearchRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


def canonical_url(url: str) -> str:
    u = urlparse(url)
    query = [(k, v) for k, v in parse_qsl(u.query) if not k.lower().startswith(_TRACKING_PREFIXES)]
    host = (u.hostname or "").lower().removeprefix("www.")
    return urlunparse(("https", host, u.path.rstrip("/"), "", urlencode(query), ""))


def record_id(url: str) -> str:
    return "src_" + hashlib.sha1(canonical_url(url).encode()).hexdigest()[:10]


def dedupe(records: list[ResearchRecord]) -> list[ResearchRecord]:
    best: dict[str, ResearchRecord] = {}
    for r in records:  # 1) same canonical URL → keep highest Tavily score
        if r.id not in best or (r.tavily_score or 0) > (best[r.id].tavily_score or 0):
            best[r.id] = r
    out: list[ResearchRecord] = []
    for r in sorted(best.values(), key=lambda x: -(x.tavily_score or 0)):  # 2) syndicated copies on same site
        if not any(r.domain == o.domain and fuzz.token_set_ratio(r.title, o.title) >= 95 for o in out):
            out.append(r)
    return out


def run_queries(branch: str, specs: list[QuerySpec]) -> BranchResult:
    res = BranchResult(usage={"tavily_searches": 0, "tavily_credits": 0, "cache_hits": 0})
    for spec in specs:
        resp = tavily_client.search(
            spec.query, branch=branch, topic=spec.topic, time_range=spec.time_range, max_results=spec.max_results
        )
        res.usage["tavily_credits"] += resp.credits
        res.usage["cache_hits" if resp.cached else "tavily_searches"] += 1
        if resp.error:
            res.errors.append(f"[{branch}] {resp.error}")
            continue
        for r in resp.results:
            content, flagged = sanitize_untrusted(r.content)
            title, title_flagged = sanitize_untrusted(r.title, max_chars=200)
            res.records.append(
                ResearchRecord(
                    id=record_id(r.url), branch=branch, query=spec.query, title=title, url=r.url, domain=r.domain,
                    content=content, published_date=r.published_date, tavily_score=r.score,
                    injection_flagged=flagged or title_flagged,
                )
            )
    res.records = dedupe(res.records)
    return res


def run_branch(branch: str, p: ProspectInput) -> BranchResult:
    return run_queries(branch, BRANCH_QUERIES[branch](p))


def merge(parts: list[BranchResult]) -> BranchResult:
    merged = BranchResult()
    for part in parts:
        merged.records += part.records
        merged.errors += part.errors
        for k, v in part.usage.items():
            merged.usage[k] = merged.usage.get(k, 0) + v
    merged.records = dedupe(merged.records)
    return merged


def research_all(p: ProspectInput) -> BranchResult:
    """Standalone (pre-LangGraph) runner: the three branches run concurrently."""
    with ThreadPoolExecutor(max_workers=3) as pool:
        parts = list(pool.map(lambda b: run_branch(b, p), BRANCH_QUERIES))
    return merge(parts)
