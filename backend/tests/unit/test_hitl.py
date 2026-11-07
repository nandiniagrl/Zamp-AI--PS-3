"""Phase 10 — human review via LangGraph interrupt/resume with checkpointing (MOCK fixture, no network)."""
import sqlite3
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from app.graph.builder import build_graph
from app.graph.routing import MAX_REGENERATIONS
from app.graph.state import initial_state

NEW_BODY = ("Hi Priya,\n\nCongrats on the Series B. Acme Analytics raised $40M to expand into Europe, and new markets "
            "usually bring more payment processors and more month-end matching work. LedgerLens automates revenue "
            "reconciliation across payment processors, so finance teams can close faster as volumes grow across "
            "regions. If Europe means adding processors this year, would a short conversation about how other "
            "finance teams handle it be useful?\n\nBest,\nAsha")


def _start(fx, saver=None, thread=None):
    graph = build_graph(saver or InMemorySaver())
    config = {"configurable": {"thread_id": thread or uuid.uuid4().hex}, "recursion_limit": 60}
    list(graph.stream(initial_state("t", fx["prospect"]), config, stream_mode="updates"))
    return graph, config


def _resume(graph, config, answer):
    return [n for c in graph.stream(Command(resume=answer), config, stream_mode="updates") for n in c]


def _pending(graph, config):
    snap = graph.get_state(config)
    return snap.interrupts[0].value if snap.interrupts else None


def test_every_draft_pauses_for_review_with_no_send_option(fakes):
    _, _, fx = fakes("happy_path")
    graph, config = _start(fx)
    pending = _pending(graph, config)
    assert pending["type"] == "review" and "never sends email" in pending["note"]
    assert set(pending["options"]) == {"approve", "edit", "reject", "choose_signal", "regenerate"}  # no "send"
    assert graph.get_state(config).values["status"] == "awaiting_review"


def test_approve_marks_ready_without_sending(fakes):
    _, _, fx = fakes("happy_path")
    graph, config = _start(fx)
    visited = _resume(graph, config, {"action": "approve"})
    state = graph.get_state(config).values
    assert visited == ["human_review"] and state["status"] == "approved"
    assert state["final_draft"]["body"] == state["draft"]["body"]
    assert state["review_log"][-1]["action"] == "approve"


def test_edit_is_rechecked_then_paused_again_and_human_text_kept(fakes):
    _, llm, fx = fakes("happy_path")
    graph, config = _start(fx)
    drafts_before = llm.calls.count("DraftOutput")
    visited = _resume(graph, config, {"action": "edit", "body": NEW_BODY})
    assert visited == ["human_review", "quality_check", "__interrupt__"]   # re-checked, never auto-rewritten
    assert llm.calls.count("DraftOutput") == drafts_before
    pending = _pending(graph, config)
    assert pending["draft"]["edited_by_human"] and pending["draft"]["version"] == 2
    _resume(graph, config, {"action": "approve"})
    assert graph.get_state(config).values["final_draft"]["body"] == NEW_BODY


def test_reject(fakes):
    _, _, fx = fakes("happy_path")
    graph, config = _start(fx)
    _resume(graph, config, {"action": "reject", "reason": "Not a fit this quarter"})
    state = graph.get_state(config).values
    assert state["status"] == "rejected" and state["review_log"][-1]["reason"] == "Not a fit this quarter"


def test_choose_another_signal_redrafts_with_that_hook(fakes):
    _, llm, fx = fakes("happy_path")
    graph, config = _start(fx)
    pending = _pending(graph, config)
    alt = pending["alternatives"][0]["evidence_id"]
    visited = _resume(graph, config, {"action": "choose_signal", "evidence_id": alt})
    assert visited[:3] == ["human_review", "draft_email", "quality_check"]
    assert _pending(graph, config)["draft"]["hook_evidence_id"] == alt
    assert f"HOOK evidence_id={alt}" in [p for c, p in zip(llm.calls, llm.prompts) if c == "DraftOutput"][-1]


def test_ineligible_signal_is_refused(fakes):
    _, _, fx = fakes("happy_path")
    graph, config = _start(fx)
    _resume(graph, config, {"action": "choose_signal", "evidence_id": "ev_not_real"})
    state = graph.get_state(config).values
    assert _pending(graph, config)["type"] == "review" and "not an eligible" in state["review_log"][-1]["error"]


def test_regenerate_passes_instructions_and_is_capped(fakes):
    _, llm, fx = fakes("happy_path")
    graph, config = _start(fx)
    _resume(graph, config, {"action": "regenerate", "instructions": "mention Europe first", "tone": "friendly"})
    last_prompt = [p for c, p in zip(llm.calls, llm.prompts) if c == "DraftOutput"][-1]
    assert "mention Europe first" in last_prompt
    assert graph.get_state(config).values["tone"] == "friendly"
    for _ in range(MAX_REGENERATIONS - 1):
        _resume(graph, config, {"action": "regenerate"})
    drafts = llm.calls.count("DraftOutput")
    _resume(graph, config, {"action": "regenerate"})  # 6th → refused
    state = graph.get_state(config).values
    assert llm.calls.count("DraftOutput") == drafts and "limit" in state["review_log"][-1]["error"]


def test_same_thread_id_preserved_across_actions(fakes):
    _, _, fx = fakes("happy_path")
    graph, config = _start(fx)
    _resume(graph, config, {"action": "regenerate", "instructions": "shorter"})
    _resume(graph, config, {"action": "approve"})
    history = list(graph.get_state_history(config))
    assert len(history) > 5 and all(h.config["configurable"]["thread_id"] == config["configurable"]["thread_id"]
                                    for h in history)
    assert [r["action"] for r in graph.get_state(config).values["review_log"]] == ["regenerate", "approve"]


def test_paused_run_survives_process_restart_with_sqlite(fakes, tmp_path):
    _, _, fx = fakes("happy_path")
    db = tmp_path / "checkpoints.sqlite"
    graph, config = _start(fx, SqliteSaver(sqlite3.connect(db, check_same_thread=False)), thread="run-123")
    assert _pending(graph, config)["type"] == "review"
    del graph  # "restart": brand-new graph object and a brand-new DB connection
    graph2 = build_graph(SqliteSaver(sqlite3.connect(db, check_same_thread=False)))
    config2 = {"configurable": {"thread_id": "run-123"}}
    assert _pending(graph2, config2)["type"] == "review"
    _resume(graph2, config2, {"action": "approve"})
    assert graph2.get_state(config2).values["status"] == "approved"
