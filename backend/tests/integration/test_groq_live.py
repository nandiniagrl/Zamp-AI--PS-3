"""Real Groq call (uses a few hundred free-tier tokens). Run with: pytest -m integration -k groq"""
import pytest
from pydantic import BaseModel

from app.config import get_settings
from app.llm import groq_client as llm

pytestmark = pytest.mark.integration


class Ping(BaseModel):
    answer: str
    confidence: str


@pytest.mark.skipif(get_settings().key_status()["GROQ_API_KEY"] == "missing", reason="GROQ_API_KEY not set")
def test_live_structured_call():
    obj, usage = llm.chat_json(Ping, system="Answer briefly.", user="Is Python a programming language? JSON please.")
    assert obj.answer
    assert usage.groq_calls >= 1 and usage.groq_prompt_tokens > 0
