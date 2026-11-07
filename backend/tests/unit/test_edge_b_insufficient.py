"""Edge Case B — insufficient public signals. Proves: broaden once → ask the user → never fabricate (MOCK)."""
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


def _resume(graph, config, answer):
    return [n for c in graph.stream(Command(resume=answer), config, stream_mode="updates") for n in c]


def test_broadens_once_then_pauses_with_clear_message(fakes):
    search, llm, fx = fakes("no_signals")
    graph, config, visited = _start(fx)
    assert visited.count("broaden_research") == 1
    assert visited[-2:] == ["rank_signals", "__interrupt__"]
    assert visited.count("rank_signals") == 2                     # ranked before and after broadening
    assert "draft_email" not in visited and "DraftOutput" not in llm.calls   # no fabricated hook
    snap = graph.get_state(config)
    pending = snap.interrupts[0].value
    assert snap.next == ("insufficient_evidence",)
    assert pending["type"] == "insufficient" and pending["message"] == "Insufficient verified research"
    assert pending["can_add_context"] is True
    assert [e["case"] for e in snap.values["edge_cases"]] == ["B"]
    assert all(e["verification_status"] != "verified" for e in snap.values["evidence"])   # rumour + broker data


def test_abstain_ends_without_draft(fakes):
    _, llm, fx = fakes("no_signals")
    graph, config, _ = _start(fx)
    visited = _resume(graph, config, {"action": "abstain"})
    state = graph.get_state(config).values
    assert visited == ["insufficient_evidence"] and state["status"] == "insufficient"
    assert not state.get("draft") and "DraftOutput" not in llm.calls


def test_user_context_triggers_one_targeted_round_and_can_lead_to_a_draft(fakes):
    search, llm, fx = fakes("no_signals")
    graph, config, _ = _start(fx)
    visited = _resume(graph, config, {"action": "add_context", "context": "Pune warehouse opening"})
    state = graph.get_state(config).values
    assert visited[:2] == ["insufficient_evidence", "broaden_research"]
    assert any("Pune warehouse opening" in q for b, q in search.calls if b == "broadened")
    assert "draft_email" in visited and state["status"] == "awaiting_review"
    hook = next(e for e in state["evidence"] if e["id"] == state["draft"]["hook_evidence_id"])
    assert hook["verification_status"] == "verified" and "economictimes" in hook["source_url"]  # verified, not user text


def test_context_round_is_bounded(fakes):
    search, _, fx = fakes("no_signals")
    graph, config, _ = _start(fx)
    _resume(graph, config, {"action": "add_context", "context": "robotics pilot"})   # finds nothing new
    pending = graph.get_state(config).interrupts[0].value
    assert pending["type"] == "insufficient" and pending["can_add_context"] is False
    _resume(graph, config, {"action": "add_context", "context": "another try"})       # refused → stops
    state = graph.get_state(config).values
    assert state["status"] == "insufficient" and not graph.get_state(config).interrupts
    assert sum(1 for b, _ in search.calls if b == "broadened") == 5                    # 2 automatic + 3 with context
