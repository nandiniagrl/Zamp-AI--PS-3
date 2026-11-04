import importlib

import pytest

from app.config import Settings


@pytest.mark.parametrize(
    "module",
    ["dotenv", "pydantic", "pydantic_settings", "groq", "tavily", "langgraph", "tenacity", "rapidfuzz"],
)
def test_dependency_imports(module):
    importlib.import_module(module)


def test_missing_keys_reported_not_crash():
    s = Settings(_env_file=None, groq_api_key=None, tavily_api_key=None)
    assert s.key_status() == {"GROQ_API_KEY": "missing", "TAVILY_API_KEY": "missing"}


def test_secrets_never_rendered():
    s = Settings(_env_file=None, groq_api_key="gsk_TESTSECRET", tavily_api_key="tvly-TESTSECRET")
    rendered = repr(s) + str(s) + str(s.model_dump())
    assert "TESTSECRET" not in rendered
    assert s.key_status() == {"GROQ_API_KEY": "present", "TAVILY_API_KEY": "present"}
