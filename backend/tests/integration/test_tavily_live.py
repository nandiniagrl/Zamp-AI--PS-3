"""Real Tavily search (1 free credit, cached for 24h). Run with: pytest -m integration -k tavily"""
import pytest

from app.config import get_settings
from app.tools import tavily_client

pytestmark = pytest.mark.integration


@pytest.mark.skipif(get_settings().key_status()["TAVILY_API_KEY"] == "missing", reason="TAVILY_API_KEY not set")
def test_live_news_search():
    r = tavily_client.search("Stripe announcements", branch="test", topic="news", max_results=3, time_range="month")
    assert r.error is None, r.error
    assert r.results and all(x.url.startswith("http") for x in r.results)
