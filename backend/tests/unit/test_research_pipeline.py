"""Phase 3 pipeline tests on MOCK fixture data (no network)."""
from app.models import ProspectInput
from app.research import pipeline, queries


def _prospect(fx) -> ProspectInput:
    return ProspectInput.model_validate(fx["prospect"])


def test_all_three_branches_searched_and_records_returned(fakes):
    search, _, fx = fakes("happy_path")
    res = pipeline.research_all(_prospect(fx))
    assert {b for b, _ in search.calls} == {"person", "company", "hiring"}
    assert {r.branch for r in res.records} == {"person", "company", "hiring"}
    assert all(r.url.startswith("https://") and r.id.startswith("src_") for r in res.records)


def test_duplicate_urls_with_tracking_params_collapse(fakes):
    _, _, fx = fakes("happy_path")
    res = pipeline.research_all(_prospect(fx))
    podcast = [r for r in res.records if "financepod" in r.url]
    assert len(podcast) == 1 and podcast[0].tavily_score == 0.82  # highest score kept


def test_injection_in_source_is_flagged_and_removed(fakes):
    _, _, fx = fakes("happy_path")
    res = pipeline.research_all(_prospect(fx))
    partner = next(r for r in res.records if "stripe-partnership" in r.url)
    assert partner.injection_flagged and "Ignore previous" not in partner.content


def test_failing_branch_reports_error_but_others_return(fakes):
    search, _, fx = fakes("happy_path")
    search.fail = {"hiring"}
    res = pipeline.research_all(_prospect(fx))
    assert any("[hiring]" in e for e in res.errors)
    assert {r.branch for r in res.records} == {"person", "company"}


def test_usage_counts_searches(fakes):
    search, _, fx = fakes("happy_path")
    res = pipeline.research_all(_prospect(fx))
    assert res.usage["tavily_searches"] == len(search.calls) == 5
    assert res.usage["tavily_credits"] == 5


def test_canonical_url_strips_tracking_and_www():
    assert pipeline.canonical_url("http://www.a.com/x/?utm_source=1&id=2#frag") == "https://a.com/x?id=2"


def test_query_builders_are_bounded():
    p = ProspectInput.model_validate({"name": "A B", "company": "Acme", "title": "VP Sales",
                                      "seller": {"product": "X1", "value_proposition": "Helps sales teams."}})
    assert len(queries.person_queries(p)) == 2 and len(queries.company_queries(p)) == 2
    assert queries.hiring_queries(p)[0].query == "Acme hiring sales jobs careers"
    assert len(queries.broadened_queries(p, "new EU office")) == 3
