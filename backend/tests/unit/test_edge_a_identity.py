"""Edge Case A — ambiguous prospect identity. Proves the graph pauses instead of guessing (MOCK fixtures)."""
import uuid

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph.builder import build_graph
from app.graph.state import initial_state
from app.identity.resolver import resolve_identity
from app.models import IdentityChoice, ProspectInput


def _start(fx):
    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": uuid.uuid4().hex}, "recursion_limit": 60}
    visited = [n for c in graph.stream(initial_state("t", fx["prospect"]), config, stream_mode="updates") for n in c]
    return graph, config, visited


def _resume(graph, config, answer):
    return [n for c in graph.stream(Command(resume=answer), config, stream_mode="updates") for n in c]


def test_ambiguous_identity_pauses_before_any_research(fakes):
    search, _, fx = fakes("identity_ambiguous")
    graph, config, visited = _start(fx)
    snap = graph.get_state(config)
    assert visited == ["resolve_prospect", "__interrupt__"]
    assert snap.next == ("identity_clarify",)
    pending = snap.interrupts[0].value
    assert pending["type"] == "identity"
    assert {c["company"] for c in pending["candidates"]} == {"Infosys", "Zeta"}
    assert {b for b, _ in search.calls} == {"identity"}            # no person/company/hiring research yet
    state = snap.values
    assert state["status"] == "awaiting_identity"
    assert state["edge_cases"][0]["case"] == "A" and "no guessing" in state["edge_cases"][0]["action"]


def test_hallucinated_candidate_not_grounded_in_snippet_is_discarded(fakes):
    _, _, fx = fakes("identity_ambiguous")
    res, _ = resolve_identity(ProspectInput.model_validate(fx["prospect"]))
    # The fake LLM claims "Rahul Sharma, CTO at Acme Analytics" from a snippet about *Ravi* Sharma.
    assert res.status == "ambiguous"
    assert all(c.company != "Acme Analytics" for c in res.candidates)


def test_resume_with_candidate_runs_research_for_that_person(fakes):
    search, _, fx = fakes("identity_ambiguous")
    graph, config, _ = _start(fx)
    zeta = next(c for c in graph.get_state(config).interrupts[0].value["candidates"] if c["company"] == "Zeta")
    visited = _resume(graph, config, {"candidate_id": zeta["id"]})
    state = graph.get_state(config).values
    assert visited[0] == "identity_clarify"
    assert {"research_person", "research_company", "research_hiring"} <= set(visited)
    assert state["identity"]["status"] == "confirmed" and state["prospect"]["company"] == "Zeta"
    assert any(b == "person" for b, _ in search.calls)


def test_resume_company_only_skips_person_research(fakes):
    search, _, fx = fakes("identity_ambiguous")
    graph, config, _ = _start(fx)
    _resume(graph, config, {"company_only": True})
    state = graph.get_state(config).values
    assert state["identity"]["status"] == "unconfirmed"
    assert not any(b == "person" for b, _ in search.calls)
    assert any("Skipped" in p["message"] for p in state["progress"] if p["node"] == "research_person")


def test_resume_abort_ends_run(fakes):
    search, _, fx = fakes("identity_ambiguous")
    graph, config, _ = _start(fx)
    visited = _resume(graph, config, {"abort": True})
    assert visited == ["identity_clarify"] and graph.get_state(config).values["status"] == "aborted"
    assert {b for b, _ in search.calls} == {"identity"}


def test_identity_choice_requires_exactly_one_option():
    with pytest.raises(ValueError):
        IdentityChoice(candidate_id="c1", abort=True)
    with pytest.raises(ValueError):
        IdentityChoice()


def test_unique_match_at_company_is_confirmed_without_pausing(fakes):
    _, _, fx = fakes("happy_path")
    graph, config, visited = _start(fx)
    assert "identity_clarify" not in visited and not graph.get_state(config).interrupts
    assert graph.get_state(config).values["identity"]["status"] == "confirmed"


def test_profile_url_confirms_without_searching(fakes):
    search, _, fx = fakes("happy_path")
    p = ProspectInput.model_validate({**fx["prospect"], "profile_url": "https://www.linkedin.com/in/example"})
    res, _ = resolve_identity(p)
    assert res.status == "confirmed" and "not fetched" in res.explanation and search.calls == []


def test_no_identity_results_continue_company_only(fakes):
    search, _, fx = fakes("happy_path")
    fx_search = search.fx
    fx_search["identity"] = []
    graph, config, visited = _start(fx)
    state = graph.get_state(config).values
    assert state["identity"]["status"] == "unconfirmed" and "identity_clarify" not in visited
    assert not any(b == "person" for b, _ in search.calls)


def test_title_synonyms_match():
    from rapidfuzz import fuzz
    from app.verification.verifier import normalize_value
    assert fuzz.token_set_ratio(normalize_value("person_role", "CEO"),
                                normalize_value("person_role", "Chief Executive Officer")) >= 70


def test_career_history_on_one_page_is_one_person(fakes):
    _, _, fx = fakes("identity_ambiguous")
    fx["llm"]["people_by_url"]["https://people.example/rahul-sharma-infosys"] += [
        {"name": "Rahul Sharma", "title": "Sales Manager", "company": "Wipro"},      # earlier job on same profile
        {"name": "Rahul Sharma", "title": "Account Executive", "company": "TCS"}]
    res, _ = resolve_identity(ProspectInput.model_validate(fx["prospect"]))
    assert sorted(c.company for c in res.candidates) == ["Infosys", "Zeta"]
