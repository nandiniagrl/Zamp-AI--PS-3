"""Offline tests for the Groq wrapper using a fake SDK client (no network, no credits)."""
import logging
from types import SimpleNamespace

import groq
import httpx
import pytest
from pydantic import BaseModel

from app.config import get_settings
from app.llm import groq_client as llm
from app.logging_setup import RedactSecrets


class Ping(BaseModel):
    answer: str
    confidence: str


def _resp(content: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )


class FakeClient:
    """Mimics client.chat.completions.create; returns queued outputs or raises queued exceptions."""

    def __init__(self, outputs):
        self.outputs, self.calls = list(outputs), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.outputs.pop(0)
        if isinstance(item, Exception):
            raise item
        return _resp(item)


def _status_error(cls, code: int):
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return cls("boom", response=httpx.Response(code, request=req), body=None)


@pytest.fixture(autouse=True)
def _no_real_env(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_missing_key_raises_friendly_error(monkeypatch):
    monkeypatch.setattr(llm, "get_settings", lambda: get_settings().model_copy(update={"groq_api_key": None}))
    with pytest.raises(llm.MissingCredentialError, match="GROQ_API_KEY is missing"):
        llm.get_client()


def test_valid_json_returns_model_and_usage():
    client = FakeClient(['{"answer": "yes", "confidence": "high"}'])
    obj, usage = llm.chat_json(Ping, system="s", user="u", client=client, model="openai/gpt-oss-120b")
    assert obj == Ping(answer="yes", confidence="high")
    assert usage.as_dict() == {"groq_calls": 1, "groq_prompt_tokens": 10, "groq_completion_tokens": 5}


def test_invalid_then_valid_json_repairs_on_second_attempt():
    client = FakeClient(['{"answer": "yes"}', '{"answer": "yes", "confidence": "high"}'])
    obj, usage = llm.chat_json(Ping, system="s", user="u", client=client, model="openai/gpt-oss-120b")
    assert obj.confidence == "high"
    assert usage.groq_calls == 2
    assert "failed validation" in client.calls[1]["messages"][-1]["content"]


def test_invalid_twice_raises_llm_error():
    client = FakeClient(["not json", '{"answer": 1}'])
    with pytest.raises(llm.LLMError, match="did not match Ping"):
        llm.chat_json(Ping, system="s", user="u", client=client, model="openai/gpt-oss-120b")


def test_plain_400_is_not_retried():
    client = FakeClient([_status_error(groq.BadRequestError, 400), '{"answer": "ok", "confidence": "low"}'])
    with pytest.raises(llm.LLMError, match="rejected the request"):
        llm.chat_json(Ping, system="s", user="u", client=client, model="llama-3.3-70b-versatile")
    assert len(client.calls) == 1


def test_json_validate_failed_400_retries():
    err = _status_error(groq.BadRequestError, 400)
    err.args = ("json_validate_failed: Failed to generate JSON",)
    client = FakeClient([err, '{"answer": "ok", "confidence": "low"}'])
    obj, usage = llm.chat_json(Ping, system="s", user="u", client=client, model="openai/gpt-oss-20b")
    assert obj.answer == "ok" and usage.groq_calls == 1 and len(client.calls) == 2


@pytest.mark.parametrize(
    "exc, message",
    [
        (_status_error(groq.AuthenticationError, 401), "rejected the API key"),
        (_status_error(groq.RateLimitError, 429), "rate/token limit"),
        (_status_error(groq.NotFoundError, 404), "not found"),
        (groq.APITimeoutError(request=httpx.Request("POST", "https://x")), "timed out"),
        (groq.APIConnectionError(request=httpx.Request("POST", "https://x")), "network"),
    ],
)
def test_sdk_errors_mapped_to_friendly_llm_error(exc, message):
    with pytest.raises(llm.LLMError, match=message):
        llm.chat_text("hi", client=FakeClient([exc]), model="openai/gpt-oss-120b")


def test_response_format_per_model_family():
    assert llm.response_format_for(Ping, "openai/gpt-oss-120b")["type"] == "json_schema"
    assert llm.response_format_for(Ping, "llama-3.3-70b-versatile") == {"type": "json_object"}


def test_gpt_oss_gets_low_reasoning_effort():
    client = FakeClient(["hello"])
    text, _ = llm.chat_text("hi", client=client, model="openai/gpt-oss-20b")
    assert text == "hello" and client.calls[0]["reasoning_effort"] == "low"


def test_log_filter_redacts_keys():
    record = logging.LogRecord("x", logging.INFO, "", 0, "key=%s", ("gsk_abcdefghijklmnop",), None)
    RedactSecrets().filter(record)
    assert "gsk_" not in record.getMessage()
