"""Phase 8: the whole prospect → draft workflow runs through LangGraph (MOCK fixture, no network)."""
import uuid

from langgraph.checkpoint.memory import InMemorySaver

from app.graph.builder import build_graph
from app.graph.state import initial_state


def _run(fx):
    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": uuid.uuid4().hex}, "recursion_limit": 60}
    steps = [list(chunk) for chunk in graph.stream(initial_state("t", fx["prospect"]), config, stream_mode="updates")]
    return [n for step in steps for n in step], graph.get_state(config).values


def test_happy_path_runs_end_to_end(fakes):
    search, llm, fx = fakes("happy_path")
    visited, state = _run(fx)
    assert visited[0] == "resolve_prospect"
    assert set(visited[1:4]) == {"research_person", "research_company", "research_hiring"}  # parallel superstep
    assert visited[4:] == ["verify_evidence", "rank_signals", "draft_email", "quality_check", "finalize_draft"]
    assert state["status"] == "draft_ready" and state["quality"]["passed"]
    top = next(r for r in state["ranked"] if r["eligible_for_hook"])
    assert state["draft"]["hook_evidence_id"] == top["evidence_id"] == state["selected_evidence_id"]
    assert "raised $40M" in top["claim"]
    # 6 sources → 2 extraction batches + rank + draft + judge = 5 Groq calls; 5 searches = 5 credits
    assert state["usage"]["groq_calls"] == 5 and state["usage"]["tavily_credits"] == 5   # summed across nodes
    assert len(state["progress"]) == len(visited)                                         # every node reported


def test_quality_loop_in_graph_is_bounded(fakes):
    _, llm, fx = fakes("happy_path")
    bad = {**fx["llm"]["DraftOutput"][0], "body": "Hi Priya, I hope this email finds you well! Quick call?"}
    fx["llm"]["DraftOutput"] = [bad]  # always flawed
    visited, state = _run(fx)
    assert visited.count("draft_email") == 3 and visited.count("quality_check") == 3   # 1 + MAX_REVISIONS
    assert state["revision_count"] == 2
    assert state["quality"]["needs_human"] and not state["quality"]["passed"]
    assert state["status"] == "draft_ready"


def test_revision_receives_feedback_then_passes(fakes):
    _, llm, fx = fakes("happy_path")
    good = fx["llm"]["DraftOutput"][0]
    fx["llm"]["DraftOutput"] = [{**good, "body": "Hi Priya, quick call?"}, good]
    visited, state = _run(fx)
    assert visited.count("draft_email") == 2 and state["quality"]["passed"]
    draft_prompts = [p for c, p in zip(llm.calls, llm.prompts) if c == "DraftOutput"]
    assert "FIX THESE ISSUES" in draft_prompts[1] and state["draft"]["version"] == 2


def test_no_eligible_signal_ends_without_draft(fakes):
    _, _, fx = fakes("happy_path")
    fx["llm"]["claims_by_url"] = {}  # nothing verifiable
    visited, state = _run(fx)
    assert "draft_email" not in visited and state["status"] == "insufficient" and not state.get("draft")


def test_graph_diagram_renders():
    mermaid = build_graph().get_graph().draw_mermaid()
    assert "research_company" in mermaid and "quality_check" in mermaid
