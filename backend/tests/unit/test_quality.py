"""Phase 7: deliberately flawed drafts are detected; the revision loop is bounded (MOCK LLM, no network)."""
import pytest

from app.llm import groq_client
from app.models import ClaimRef, Draft, Evidence, ProspectInput
from app.quality import loop
from app.quality.checker import check_draft
from app.quality.rules import run_rules
from app.utils.text import word_count
from tests.fakes import FakeLLM

P = ProspectInput.model_validate({"name": "Priya Menon", "company": "Acme Analytics", "title": "VP Finance",
                                  "seller": {"product": "LedgerLens",
                                             "value_proposition": "Automates revenue reconciliation across processors."}})
HOOK = Evidence(id="ev_hook", claim="Acme Analytics raised $40M to expand into Europe", claim_type="funding",
                subject="company", key="k", quote="Acme Analytics raised $40M in a Series B round to expand into Europe.",
                source_url="https://techcrunch.com/x", source_title="t", source_domain="techcrunch.com",
                association="company", base_status="verified", verification_status="verified", credibility="high",
                credibility_reason="r")
ALLOWED = {"ev_hook": HOOK}
CLEAN_BODY = ("Hi Priya,\n\nSaw that Acme Analytics raised $40M to expand into Europe. New markets usually mean more "
              "payment processors and more reconciliation work at month-end. LedgerLens automates revenue "
              "reconciliation across processors, so the finance team spends less time matching transactions by "
              "hand as volumes grow. If Europe is adding processors to your stack this year, it could be useful to "
              "compare notes on how other finance teams are handling it. Would a short conversation be useful?"
              "\n\nBest,\n[Your name]")
FLAWED_BODY = ("Hi Priya,\n\nI hope this email finds you well! Your visionary leadership is amazing. "
               + "We help companies like yours do more with less every single day. " * 10
               + "LedgerLens customers cut costs by 40% in a month. Let me know when [Company] is free."
               "\n\nBest,\n[Your name]")


def _draft(body, claims=(("Acme raised $40M", "ev_hook"),), subject="Acme's Europe expansion"):
    return Draft(subject=subject, body=body, hook_evidence_id="ev_hook", word_count=word_count(body),
                 claims_used=[ClaimRef(text=t, evidence_id=e) for t, e in claims])


def test_clean_draft_has_no_failures():
    assert [i for i in run_rules(_draft(CLEAN_BODY), ALLOWED, P.seller.as_text()) if i.severity == "fail"] == []


def test_deliberately_flawed_draft_is_detected():
    d = _draft(FLAWED_BODY, claims=[("Acme won an award", "ev_unknown")], subject="Quick question!!!")
    checks = {(i.check, i.severity) for i in run_rules(d, ALLOWED, P.seller.as_text())}
    for expected in ["conciseness", "generic_language", "tone", "unsupported_claim", "hook", "cta", "placeholder"]:
        assert (expected, "fail") in checks, expected
    msgs = " ".join(i.message for i in run_rules(d, ALLOWED, P.seller.as_text()))
    assert "40%" in msgs and "hope this email finds you well" in msgs


def test_figure_present_in_evidence_is_allowed():
    issues = run_rules(_draft(CLEAN_BODY), ALLOWED, P.seller.as_text())
    assert not any(i.check == "unsupported_claim" for i in issues)  # "$40M" is in the hook quote


def _judge(**overrides):
    base = {"factual_statements_supported": True, "unsupported_statements": [], "hook_relevant_to_offer": True,
            "specific_not_generic": True, "seller_claims_supported": True, "tone_appropriate": True}
    return {**base, **overrides}


def test_llm_judge_failures_become_actionable_feedback(monkeypatch):
    fake = FakeLLM({"llm": {"QualityJudgement": [_judge(seller_claims_supported=False,
                                                        unsupported_statements=["without building custom tooling"])]}})
    monkeypatch.setattr(groq_client, "chat_json_patient", fake)
    report, _ = check_draft(_draft(CLEAN_BODY), P, ALLOWED)
    assert not report.passed and not report.checks["seller_claims_supported"]
    assert any("without building custom tooling" in f for f in report.revision_feedback)


def test_judge_unavailable_means_needs_human_not_pass(monkeypatch):
    def boom(schema, **kw):
        raise groq_client.LLMError("Groq rate/token limit reached (429)")
    monkeypatch.setattr(groq_client, "chat_json_patient", boom)
    report, _ = check_draft(_draft(CLEAN_BODY), P, ALLOWED)
    assert not report.passed and report.needs_human


def _loop_llm(monkeypatch, drafts, judgements):
    fake = FakeLLM({"llm": {"DraftOutput": drafts, "QualityJudgement": judgements}})
    monkeypatch.setattr(groq_client, "chat_json_patient", fake)
    return fake


def test_flawed_then_clean_passes_on_attempt_two(monkeypatch):
    fake = _loop_llm(monkeypatch,
                     [{"subject": "Hi", "body": FLAWED_BODY, "claims_text": ["x"]},
                      {"subject": "Acme's Europe expansion", "body": CLEAN_BODY, "claims_text": ["Acme raised $40M"]}],
                     [_judge(tone_appropriate=False), _judge()])
    res = loop.draft_until_pass(P, HOOK, [])
    assert res.report.passed and res.attempts == 2 and res.draft.version == 2
    assert "FIX THESE ISSUES" in fake.prompts[2]  # 2nd DraftOutput prompt carries the feedback


def test_always_flawed_stops_after_three_and_flags_human(monkeypatch):
    fake = _loop_llm(monkeypatch, [{"subject": "Hi", "body": FLAWED_BODY, "claims_text": ["x"]}],
                     [_judge(tone_appropriate=False)])
    res = loop.draft_until_pass(P, HOOK, [])
    assert res.attempts == 3 and not res.report.passed and res.report.needs_human
    assert fake.calls.count("DraftOutput") == 3
