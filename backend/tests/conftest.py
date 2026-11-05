import pytest

from app.config import get_settings
from app.llm import groq_client
from app.tools import tavily_client
from tests.fakes import FakeLLM, FakeSearch, load_fixture


def _blocked(*args, **kwargs):
    raise AssertionError("Real API call attempted in an offline unit test")


@pytest.fixture(autouse=True)
def _offline(monkeypatch, tmp_path, request):
    """Unit tests never reach the network: the SDK entry points raise if called."""
    if request.node.get_closest_marker("integration"):
        yield
        return
    import groq.resources.chat.completions as groq_chat
    from tavily import TavilyClient

    monkeypatch.setattr(groq_chat.Completions, "create", _blocked)
    monkeypatch.setattr(TavilyClient, "search", _blocked)
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fakes(monkeypatch):
    """install('happy_path') → (FakeSearch, FakeLLM, fixture dict), patched into the app modules."""

    def install(fixture_name: str):
        fx = load_fixture(fixture_name)
        search, llm = FakeSearch(fx), FakeLLM(fx)
        monkeypatch.setattr(tavily_client, "search", search)
        monkeypatch.setattr(groq_client, "chat_json", llm)
        return search, llm, fx

    return install
