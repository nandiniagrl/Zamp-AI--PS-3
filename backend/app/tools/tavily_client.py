"""Tavily web search via the official tavily-python SDK.

Guarantees: timeout, at most 2 attempts for transient errors, 24h cache, structured output,
and it NEVER raises on search failure — errors are returned in SearchResponse.error so the
workflow can continue with other branches.
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field
from tavily import TavilyClient
from tavily import errors as tavily_errors
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.tools import cache

log = logging.getLogger(__name__)

# Errors that will not improve on retry (bad key, out of credits, bad params, forbidden).
_NON_RETRYABLE = tuple(
    getattr(tavily_errors, name)
    for name in ("InvalidAPIKeyError", "UsageLimitExceededError", "MissingAPIKeyError", "BadRequestError", "ForbiddenError")
    if hasattr(tavily_errors, name)
)
_FRIENDLY = {
    "InvalidAPIKeyError": "Tavily rejected the API key (401). Check TAVILY_API_KEY in backend/.env.",
    "UsageLimitExceededError": "Tavily credit/rate limit reached (429). Check usage at app.tavily.com.",
    "TavilyKeylessLimitError": "Tavily keyless limit reached. Add TAVILY_API_KEY.",
    "MissingAPIKeyError": "TAVILY_API_KEY is missing. Add it to backend/.env.",
    "ForbiddenError": "Tavily refused the request (403).",
    "BadRequestError": "Tavily rejected the query parameters (400).",
    "TimeoutError": "Tavily search timed out.",
}


class SearchResult(BaseModel):
    title: str = ""
    url: str
    content: str = ""
    score: float | None = None
    published_date: str | None = None
    domain: str = ""


class SearchResponse(BaseModel):
    query: str
    branch: str
    results: list[SearchResult] = Field(default_factory=list)
    credits: int = 0
    cached: bool = False
    error: str | None = None


def domain_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _retryable(exc: BaseException) -> bool:
    return not isinstance(exc, _NON_RETRYABLE)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception(_retryable),
    reraise=True,
)
def _raw_search(client: TavilyClient, **params) -> dict:
    return client.search(**params)


def _describe(exc: Exception) -> str:
    if isinstance(exc, requests.HTTPError):
        return f"Tavily HTTP error {getattr(exc.response, 'status_code', '?')}."
    if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
        return "Could not reach Tavily (network error or timeout)."
    return _FRIENDLY.get(type(exc).__name__, f"Tavily search failed ({type(exc).__name__}).")


def search(
    query: str,
    *,
    branch: str = "general",
    topic: str = "general",
    time_range: str | None = None,
    max_results: int | None = None,
    depth: str = "basic",
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> SearchResponse:
    """One bounded Tavily search. `branch` labels which research branch asked (person/company/...)."""
    s = get_settings()
    params: dict = {
        "query": query[:400],
        "topic": topic,
        "search_depth": depth,  # "basic" = 1 credit, "advanced" = 2 credits
        "max_results": min(max_results or s.tavily_max_results, 10),
        "include_answer": False,
        "include_raw_content": False,
        "auto_parameters": False,  # auto mode can silently switch to advanced (2 credits)
    }
    if time_range:
        params["time_range"] = time_range
    if include_domains:
        params["include_domains"] = include_domains
    if exclude_domains:
        params["exclude_domains"] = exclude_domains

    key = cache.make_key("tavily", params)
    if (hit := cache.get(key)) is not None:
        return SearchResponse(query=query, branch=branch, results=[SearchResult(**r) for r in hit], cached=True)

    if s.tavily_api_key is None or not s.tavily_api_key.get_secret_value().strip():
        return SearchResponse(query=query, branch=branch, error=_FRIENDLY["MissingAPIKeyError"])

    try:
        client = TavilyClient(api_key=s.tavily_api_key.get_secret_value())
        raw = _raw_search(client, timeout=s.tavily_timeout_s, **params)
    except Exception as exc:  # a failed search must never crash the workflow
        log.warning("Tavily search failed (branch=%s): %s", branch, type(exc).__name__)
        return SearchResponse(query=query, branch=branch, error=_describe(exc))

    results = [
        SearchResult(
            title=r.get("title") or "",
            url=r["url"],
            content=(r.get("content") or "")[:4000],
            score=r.get("score"),
            published_date=r.get("published_date"),
            domain=domain_of(r["url"]),
        )
        for r in raw.get("results", [])
        if r.get("url")
    ]
    cache.set(key, [r.model_dump() for r in results])
    return SearchResponse(query=query, branch=branch, results=results, credits=2 if depth == "advanced" else 1)
