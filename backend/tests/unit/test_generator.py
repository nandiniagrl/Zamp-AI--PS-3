"""Phase 6 draft generator tests (MOCK LLM output, no network)."""
import pytest

from app.drafting.generator import build_prompts, generate_draft
from app.llm import groq_client
from app.models import Evidence, ProspectInput
from tests.fakes import FakeLLM

P = ProspectInput.model_validate({"name": "Priya Menon", "company": "Acme Analytics", "title": "VP Finance",
                                  "seller": {"product": "LedgerLens",
                                             "value_proposition": "Automates revenue reconciliation across processors."}})


def _ev(eid, claim, status="verified"):
    return Evidence(id=eid, claim=claim, claim_type="funding", subject="company", key="k", quote=f"{claim} (quote)",
                    source_url=f"https://src/{eid}", source_title="t", source_domain="techcrunch.com",
                    publication_date="2026-09-12", association="company", base_status=status,
                    verification_status=status, credibility="high", credibility_reason="r")


HOOK = _ev("ev_hook", "Acme Analytics raised $40M to expand into Europe")
SUP = [_ev("ev_sup", "Acme Analytics is hiring a revenue accountant"), _ev("ev_extra", "Acme partners with Stripe")]
BODY = ("Hi Priya,\n\nSaw that Acme Analytics raised $40M to expand into Europe. New markets usually mean more "
        "payment processors and more reconciliation work at month-end. LedgerLens automates revenue reconciliation "
        "across processors so finance teams can close faster without adding headcount for manual matching. If "
        "Europe is adding processors to your stack this year, it might be worth comparing notes on how other "
        "finance teams handle it. Would a short conversation next month be useful?\n\nBest,\n[Your name]")


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM({"llm": {"DraftOutput": [{"subject": "Acme's Europe expansion and month-end close",
                                             "body": BODY, "claims_text": ["Acme raised $40M to expand into Europe"]}]}})
    monkeypatch.setattr(groq_client, "chat_json_patient", fake)
    return fake


def test_prompt_contains_only_hook_and_one_supporting_fact():
    system, user = build_prompts(P, HOOK, SUP, tone="friendly", instructions="mention Europe",
                                 feedback=["Remove the phrase 'touch base'."])
    assert "HOOK evidence_id=ev_hook" in user and "ev_sup" in user
    assert "ev_extra" not in user and "Stripe" not in user          # max one supporting fact
    assert "REVIEWER INSTRUCTIONS" in user and "mention Europe" in user
    assert "touch base" in user and "FIX THESE ISSUES" in user
    assert "friendly and conversational" in system and "Hi Priya," in system
    assert "70-110 words" in system


def test_generate_parses_draft_and_counts_words(llm):
    draft, usage = generate_draft(P, HOOK, SUP, tone="professional", version=2)
    assert draft.subject.startswith("Acme's Europe")
    assert draft.hook_evidence_id == "ev_hook" and draft.supporting_evidence_ids == ["ev_sup"]
    assert draft.claims_used[0].evidence_id == "ev_hook"
    assert 70 <= draft.word_count <= 110 and draft.version == 2 and not draft.edited_by_human
    assert usage["groq_calls"] == 1


def test_missing_signoff_is_added_once():
    from app.drafting.generator import ensure_signoff
    assert ensure_signoff("Hi Priya, would a chat help?").endswith("Best,\n[Your name]")
    already = "Hi Priya, would a chat help?\n\nBest,\n[Your name]"
    assert ensure_signoff(already) == already
