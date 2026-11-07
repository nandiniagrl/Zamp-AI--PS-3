"""Edge Case D — conflicting or outdated evidence (MOCK fixtures, no network)."""
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph.builder import build_graph
from app.graph.state import initial_state


def _start(fx):
    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": uuid.uuid4().hex}, "recursion_limit": 60}
    visited = [n for c in graph.stream(initial_state("t", fx["prospect"]), config, stream_mode="updates") for n in c]
    return graph, config, visited


def _role_evidence(state):
    return {e["value"]: e for e in state["evidence"] if e["claim_type"] == "person_role"}


def test_conflict_resolved_by_targeted_verification_and_strength_not_recency(fakes):
    search, _, fx = fakes("conflicting_role")
    graph, config, visited = _start(fx)
    state = graph.get_state(config).values
    assert visited.count("targeted_verification") == 1 and visited.count("verify_evidence") == 2
    assert any(b == "targeted" and "role" in q for b, q in search.calls)
    role = [c for c in state["conflicts"] if c["claim_type"] == "person_role"][0]
    assert role["status"] == "resolved" and "VP Finance" in role["note"]
    roles = _role_evidence(state)
    assert roles["VP Finance"]["verification_status"] == "verified"
    assert roles["Head of Finance"]["verification_status"] == "rejected"     # the NEWER source loses on strength
    assert "conflict_review" not in visited and state["status"] == "draft_ready"
    d_edges = [e for e in state["edge_cases"] if e["case"] == "D"]
    assert any("targeted" in e["action"] for e in d_edges) and any("Resolved" in e["action"] for e in d_edges)


def test_unresolved_identity_conflict_pauses_for_reviewer(fakes):
    _, llm, fx = fakes("conflicting_unresolved")
    graph, config, visited = _start(fx)
    snap = graph.get_state(config)
    assert visited.count("targeted_verification") == 1 and snap.next == ("conflict_review",)
    pending = snap.interrupts[0].value
    assert pending["type"] == "conflict" and len(pending["conflicts"]) == 1
    assert {e["value"] for e in pending["conflicts"][0]["evidence"]} == {"VP Finance", "Head of Finance"}
    assert all(e["verification_status"] == "disputed" for e in pending["conflicts"][0]["evidence"])
    assert "DraftOutput" not in llm.calls


def test_reviewer_resolution_continues_with_chosen_value(fakes):
    _, _, fx = fakes("conflicting_unresolved")
    graph, config, _ = _start(fx)
    conflict = graph.get_state(config).interrupts[0].value["conflicts"][0]
    vp = next(e for e in conflict["evidence"] if e["value"] == "VP Finance")
    visited = [n for c in graph.stream(Command(resume={"resolutions": {conflict["id"]: vp["id"]}}), config,
                                       stream_mode="updates") for n in c]
    state = graph.get_state(config).values
    assert visited[:2] == ["conflict_review", "rank_signals"] and state["status"] == "draft_ready"
    roles = _role_evidence(state)
    assert roles["VP Finance"]["verification_status"] == "verified"
    assert roles["Head of Finance"]["verification_status"] == "rejected"
    assert next(c for c in state["conflicts"] if c["id"] == conflict["id"])["status"] == "user_resolved"


def test_reviewer_can_exclude_or_abort(fakes):
    _, _, fx = fakes("conflicting_unresolved")
    graph, config, _ = _start(fx)
    cid = graph.get_state(config).interrupts[0].value["conflicts"][0]["id"]
    list(graph.stream(Command(resume={"resolutions": {cid: "exclude"}}), config, stream_mode="updates"))
    state = graph.get_state(config).values
    assert all(e["verification_status"] == "rejected" for e in _role_evidence(state).values())

    graph2, config2, _ = _start(fx)
    list(graph2.stream(Command(resume={"abort": True}), config2, stream_mode="updates"))
    assert graph2.get_state(config2).values["status"] == "aborted"


def test_unresolved_business_fact_is_excluded_and_never_used(fakes):
    _, _, fx = fakes("conflicting_funding")
    graph, config, visited = _start(fx)
    state = graph.get_state(config).values
    funding = [c for c in state["conflicts"] if c["claim_type"] == "funding"][0]
    assert funding["status"] == "excluded" and "conflict_review" not in visited
    disputed = {e["id"] for e in state["evidence"] if e["verification_status"] == "disputed"}
    assert len(disputed) == 2
    assert not disputed & {c["evidence_id"] for c in state["draft"]["claims_used"]}
    assert state["draft"]["hook_evidence_id"] not in disputed
    assert "$40M" not in state["draft"]["body"] and "$60M" not in state["draft"]["body"]
    assert any(e["case"] == "D" and "excluded" in e["action"] for e in state["edge_cases"])
