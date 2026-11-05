"""Phase 5 ranking tests with three competing MOCK signals (no network)."""
from datetime import date

import pytest

from app.llm import groq_client
from app.models import DimensionScores, Evidence, ProspectInput
from app.ranking import rubric
from app.ranking.ranker import rank_signals
from tests.fakes import FakeLLM

TODAY = date(2026, 11, 5)
P = ProspectInput.model_validate({"name": "Priya Menon", "company": "Acme Analytics", "title": "VP Finance",
                                  "seller": {"product": "LedgerLens", "value_proposition": "Automates revenue reconciliation."}})


def _ev(eid, claim, cred="high", date_="2026-10-20", sensitive=False, status="verified", corroborated=False):
    return Evidence(id=eid, claim=claim, claim_type="other", subject="company", key="k", quote="q" * 20,
                    source_url=f"https://src/{eid}", source_title="t", source_domain="techcrunch.com",
                    publication_date=date_, association="company", base_status=status, verification_status=status,
                    credibility=cred, credibility_reason="r", is_sensitive=sensitive,
                    sensitive_category="layoffs" if sensitive else None,
                    corroborating_urls=["https://other"] if corroborated else [])


COMPETING = [
    _ev("ev_fund", "Acme Analytics raised $40M to expand into Europe", corroborated=True),
    _ev("ev_trend", "Finance teams everywhere are adopting automation", cred="medium", date_="2025-01-10"),
    _ev("ev_layoff", "Acme Analytics lays off 12% of staff", sensitive=True),
    _ev("ev_rumour", "Acme might be acquired", status="uncertain"),
]
SCORES = {"raised": {"r": 8, "s": 8, "u": 7}, "everywhere": {"r": 6, "s": 2, "u": 4}, "lays off": {"r": 10, "s": 10, "u": 5}}  # layoff = 93.0 > fund 86.0


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM({"llm": {"scores": SCORES}})
    monkeypatch.setattr(groq_client, "chat_json_patient", fake)
    return fake


def test_weights_sum_to_one_and_total_is_deterministic():
    assert sum(rubric.WEIGHTS.values()) == pytest.approx(1.0)
    all10 = DimensionScores(business_relevance=10, specificity=10, credibility=10, recency=10, outreach_usefulness=10)
    assert rubric.total(all10) == 100.0
    mix = DimensionScores(business_relevance=8, specificity=8, credibility=10, recency=10, outreach_usefulness=7)
    assert rubric.total(mix) == 10 * (0.3 * 8 + 0.25 * 8 + 0.2 * 10 + 0.15 * 10 + 0.1 * 7)  # 86.0


@pytest.mark.parametrize("pub, expected", [("2026-10-25", 10), ("2026-08-20", 8), ("2026-06-01", 6),
                                           ("2026-01-01", 4), ("2024-01-01", 2), (None, 3)])
def test_recency_buckets(pub, expected):
    assert rubric.recency_score(_ev("x", "c", date_=pub), TODAY) == expected


def test_three_competing_signals_ranked_with_rationale(llm):
    res = rank_signals(P, COMPETING, today=TODAY)
    ids = [r.evidence_id for r in res.ranked]
    assert "ev_rumour" not in ids                                   # only verified evidence is ranked
    assert ids[0] == "ev_layoff"                                    # highest raw score…
    layoff = res.ranked[0]
    assert not layoff.eligible_for_hook and "Sensitive" in layoff.ineligible_reason   # …but never a hook
    eligible = [r for r in res.ranked if r.eligible_for_hook]
    assert eligible[0].evidence_id == "ev_fund"
    assert eligible[0].total > next(r.total for r in res.ranked if r.evidence_id == "ev_trend")
    assert "Recommended hook" in res.top_explanation and "sensitive" in res.top_explanation
    assert "not calibrated probabilities" in res.top_explanation
    assert "ev_rumour" not in llm.prompts[0]                        # uncertain evidence never sent to the LLM


def test_credibility_and_recency_not_from_llm(llm):
    res = rank_signals(P, COMPETING, today=TODAY)
    fund = next(r for r in res.ranked if r.evidence_id == "ev_fund")
    assert fund.scores.credibility == 10 and fund.scores.recency == 10   # high + corroborated, 16 days old


def test_missing_assessment_gets_default_low_score(monkeypatch):
    monkeypatch.setattr(groq_client, "chat_json_patient",
                        lambda schema, **kw: (schema.model_validate({"assessments": []}), groq_client.LLMUsage()))
    res = rank_signals(P, COMPETING[:1], today=TODAY)
    assert res.ranked[0].scores.business_relevance == 3 and "Not assessed" in res.ranked[0].explanation


def test_no_verified_signals():
    res = rank_signals(P, [COMPETING[3]], today=TODAY)
    assert res.ranked == [] and "No verified signals" in res.top_explanation
