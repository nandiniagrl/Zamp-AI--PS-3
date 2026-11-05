"""Phase 4 verification tests on MOCK data (no network)."""
from app.models import ConflictDecision, Evidence, ProspectInput
from app.research.pipeline import research_all
from app.verification import verifier
from app.verification.verifier import detect_conflicts, normalize_value, quote_supported, resolve_conflicts


def _run(fakes):
    _, llm, fx = fakes("happy_path")
    p = ProspectInput.model_validate(fx["prospect"])
    res = verifier.verify(p, research_all(p).records)
    return {e.claim: e for e in res.evidence}, res, llm


def test_status_paths(fakes):
    ev, res, _ = _run(fakes)
    funding = next(e for k, e in ev.items() if "raised $40" in k)
    assert funding.verification_status == "verified" and funding.credibility == "high"
    assert any("businesswire" in u for u in funding.corroborating_urls)            # duplicate merged as corroboration
    assert sum(e.claim_type == "funding" for e in res.evidence) == 1
    award = next(e for k, e in ev.items() if "award" in k)
    assert award.verification_status == "rejected" and "Quote not found" in award.notes[0]
    chef = next(e for k, e in ev.items() if "restaurant" in k)
    assert chef.verification_status == "uncertain" and chef.association == "unclear"   # namesake
    podcast = next(e for k, e in ev.items() if "month-end" in k)
    assert podcast.verification_status == "uncertain" and podcast.credibility == "low"
    hiring = next(e for e in res.evidence if e.claim_type == "hiring")
    assert hiring.verification_status == "verified" and hiring.credibility == "medium"
    assert res.conflicts == []                                                      # $40M == $40 million


def test_injected_source_downgraded_but_fact_kept(fakes):
    ev, _, _ = _run(fakes)
    partner = next(e for e in ev.values() if e.claim_type == "partnership")
    assert partner.credibility == "medium"                                          # official(high) → downgraded
    assert any("instruction-like" in n for n in partner.notes)
    assert not any("award" in e.claim.lower() and e.verification_status == "verified" for e in ev.values())


def test_llm_prompt_wraps_sources_as_untrusted(fakes):
    _, _, llm = _run(fakes)
    assert "UNTRUSTED" not in llm.prompts[0]  # notice lives in the system prompt
    assert '<source id="src_' in llm.prompts[0]


def test_quote_support_exact_fuzzy_and_short():
    content = "Acme Analytics raised $40M in a Series B round to expand into Europe."
    assert quote_supported("Acme Analytics raised $40M in a Series B round", content)
    assert quote_supported("Acme Analytics raised $40M in a Series-B round", content)
    assert not quote_supported("Acme Analytics won an award for design", content)
    assert not quote_supported("Acme", content)


def test_claim_must_be_grounded_in_its_quote():
    from app.verification.verifier import claim_grounded
    quote = "Stripe CEO Patrick Collison and John Collison gave a rundown of the firm's performance over 2025"
    assert not claim_grounded("Collison said blockchains may need 1 billion transactions per second", quote)
    assert claim_grounded("Patrick Collison gave a rundown of Stripe's 2025 performance", quote)
    assert not claim_grounded("Acme raised $60M", "Acme raised $40M in a Series B")


def _ev(i, value, domain, cred="medium", ctype="funding", key="funding_round"):
    return Evidence(id=f"ev_{i}", claim=f"claim {i}", claim_type=ctype, subject="company", key=key, value=value,
                    quote="q" * 20, source_url=f"https://{domain}/{i}", source_title="t", source_domain=domain,
                    association="company", base_status="verified", verification_status="verified",
                    credibility=cred, credibility_reason="r")


def test_money_normalisation():
    assert normalize_value("funding", "$40M Series B") == normalize_value("funding", "40 million") == "40000000"
    assert normalize_value("person_role", "Vice President Sales") == "vp sales"


def test_conflict_resolved_by_strength_not_recency():
    evs = [_ev(1, "$40M", "techcrunch.com", "high"), _ev(2, "$40 million", "reuters.com", "high"),
           _ev(3, "$60M", "newblog.example", "low")]
    conflicts = detect_conflicts(evs)
    assert len(conflicts) == 1 and len(conflicts[0].values) == 2
    evs, conflicts = resolve_conflicts(evs, conflicts, "Acme")
    assert conflicts[0].status == "resolved"
    assert {e.id: e.verification_status for e in evs} == {"ev_1": "verified", "ev_2": "verified", "ev_3": "rejected"}


def test_comparable_conflict_disputed_then_excluded():
    evs = [_ev(1, "$40M", "techcrunch.com", "high"), _ev(2, "$60M", "reuters.com", "high")]
    evs, c = resolve_conflicts(evs, detect_conflicts(evs), "Acme")
    assert c[0].status == "unresolved" and all(e.verification_status == "disputed" for e in evs)
    evs2 = [_ev(1, "$40M", "techcrunch.com", "high"), _ev(2, "$60M", "reuters.com", "high")]
    _, c2 = resolve_conflicts(evs2, detect_conflicts(evs2), "Acme", exclude_unresolved=True)
    assert c2[0].status == "excluded"


def test_identity_conflicts_never_auto_excluded_and_reviewer_can_resolve():
    evs = [_ev(1, "Head of Sales", "techcrunch.com", "high", "person_role", "role"),
           _ev(2, "VP Sales", "reuters.com", "high", "person_role", "role")]
    evs, c = resolve_conflicts(evs, detect_conflicts(evs), "Acme", exclude_unresolved=True)
    assert c[0].status == "unresolved"
    evs, c = verifier.apply_conflict_decisions(evs, c, ConflictDecision(resolutions={c[0].id: "ev_2"}))
    assert c[0].status == "user_resolved"
    assert {e.id: e.verification_status for e in evs} == {"ev_1": "rejected", "ev_2": "verified"}
