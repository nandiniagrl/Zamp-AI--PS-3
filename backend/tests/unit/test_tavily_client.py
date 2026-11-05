"""Offline tests for the Tavily wrapper: the SDK call (_raw_search) is replaced, so no credits are used."""
import pytest
from pydantic import SecretStr
from tavily import errors as tavily_errors

from app.config import get_settings
from app.tools import tavily_client as tc

RAW = {
    "results": [
        {"title": "Acme launches X", "url": "https://www.acme.com/news/x", "content": "Acme launched X today.",
         "score": 0.91, "published_date": "Mon, 03 Nov 2025 10:00:00 GMT"},
        {"title": "No url row"},  # dropped
    ]
}


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    get_settings.cache_clear()
    s = get_settings().model_copy(update={"cache_dir": tmp_path / "cache", "cache_enabled": True,
                                          "tavily_api_key": SecretStr("tvly-test")})
    monkeypatch.setattr(tc, "get_settings", lambda: s)
    monkeypatch.setattr("app.tools.cache.get_settings", lambda: s)
    yield s
    get_settings.cache_clear()


def _patch_raw(monkeypatch, side_effects):
    calls = []

    def fake(client, **params):
        calls.append(params)
        item = side_effects.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(tc.TavilyClient, "search", lambda self, **p: fake(self, **p))
    return calls


def test_results_are_mapped_and_rows_without_url_dropped(monkeypatch):
    calls = _patch_raw(monkeypatch, [RAW])
    r = tc.search("acme news", branch="company", topic="news")
    assert r.error is None and r.credits == 1 and not r.cached
    assert [x.domain for x in r.results] == ["acme.com"]
    assert r.results[0].published_date.startswith("Mon, 03 Nov 2025")
    assert calls[0]["auto_parameters"] is False and calls[0]["search_depth"] == "basic"


def test_second_identical_call_hits_cache_for_zero_credits(monkeypatch):
    calls = _patch_raw(monkeypatch, [RAW])
    tc.search("acme news")
    again = tc.search("acme news")
    assert again.cached and again.credits == 0 and len(again.results) == 1
    assert len(calls) == 1


def test_invalid_key_is_not_retried_and_returns_friendly_error(monkeypatch):
    calls = _patch_raw(monkeypatch, [tavily_errors.InvalidAPIKeyError("bad"), RAW])
    r = tc.search("acme")
    assert r.results == [] and "rejected the API key" in r.error
    assert len(calls) == 1


def test_transient_error_retried_once_then_succeeds(monkeypatch):
    monkeypatch.setattr(tc._raw_search.retry, "sleep", lambda s: None)
    calls = _patch_raw(monkeypatch, [ConnectionResetError("flaky"), RAW])
    r = tc.search("acme")
    assert r.error is None and len(calls) == 2


def test_persistent_error_gives_error_not_crash(monkeypatch):
    monkeypatch.setattr(tc._raw_search.retry, "sleep", lambda s: None)
    calls = _patch_raw(monkeypatch, [RuntimeError("x"), RuntimeError("y")])
    r = tc.search("acme")
    assert r.error and "RuntimeError" in r.error and len(calls) == 2


def test_missing_key_never_calls_tavily(monkeypatch, _isolated):
    monkeypatch.setattr(tc, "get_settings", lambda: _isolated.model_copy(update={"tavily_api_key": None}))
    calls = _patch_raw(monkeypatch, [RAW])
    r = tc.search("acme")
    assert "missing" in r.error and calls == []


def test_max_results_capped_at_10(monkeypatch):
    calls = _patch_raw(monkeypatch, [RAW])
    tc.search("acme", max_results=50)
    assert calls[0]["max_results"] == 10
