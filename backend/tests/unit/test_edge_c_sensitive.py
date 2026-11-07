"""Edge Case C — sensitive or negative company news (MOCK fixtures, no network)."""
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph.builder import build_graph
from app.graph.state import initial_state
from app.quality.checker import JUDGE_SYSTEM


def _start(fx):
    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": uuid.uuid4().hex}, "recursion_limit": 60}
    visited = [n for c in graph.stream(initial_state("t", fx["prospect"]), config, stream_mode="updates") for n in c]
    return graph, config, visited


def test_sensitive_top_signal_is_skipped_for_best_alternative(fakes):
    _, llm, fx = fakes("sensitive_news")
    graph, config, visited = _start(fx)
    state = graph.get_state(config).values
    top = state["ranked"][0]
    assert top["is_sensitive"] and top["sensitive_category"] == "layoffs" and not top["eligible_for_hook"]
    hook = next(e for e in state["evidence"] if e["id"] == state["draft"]["hook_evidence_id"])
    assert not hook["is_sensitive"] and "raised $40M" in hook["claim"]            # best non-sensitive alternative
    assert "lays off" not in state["draft"]["body"].lower()
    edge = [e for e in state["edge_cases"] if e["case"] == "C"]
    assert len(edge) == 1 and "layoffs" in edge[0]["message"] and "non-sensitive" in edge[0]["action"]
    assert "skipped because it is sensitive" in state["top_explanation"]
    assert "sensitive_judgment" not in visited and state["status"] == "awaiting_review"
    draft_prompt = next(p for c, p in zip(llm.calls, llm.prompts) if c == "DraftOutput")
    assert "lays off" not in draft_prompt.lower()                                   # never even shown to the writer


def test_only_sensitive_signals_broadens_then_asks_for_judgment(fakes):
    _, llm, fx = fakes("sensitive_only")
    graph, config, visited = _start(fx)
    snap = graph.get_state(config)
    assert visited.count("broaden_research") == 1 and "draft_email" not in visited
    assert snap.next == ("sensitive_judgment",)
    pending = snap.interrupts[0].value
    assert pending["type"] == "sensitive" and "opportunistic" in pending["detail"]
    assert {s["sensitive_category"] for s in pending["signals"]} == {"security incident", "legal"}
    assert "DraftOutput" not in llm.calls
    assert sum(e["case"] == "C" for e in snap.values["edge_cases"]) == 1   # not repeated after broadening


def test_abstain_on_sensitive_ends_without_draft(fakes):
    _, llm, fx = fakes("sensitive_only")
    graph, config, _ = _start(fx)
    visited = [n for c in graph.stream(Command(resume={"action": "abstain"}), config, stream_mode="updates") for n in c]
    state = graph.get_state(config).values
    assert visited == ["sensitive_judgment"] and state["status"] == "abstained" and not state.get("draft")


def test_quality_judge_checks_for_opportunistic_tone():
    assert "not opportunistic about sensitive events" in JUDGE_SYSTEM
