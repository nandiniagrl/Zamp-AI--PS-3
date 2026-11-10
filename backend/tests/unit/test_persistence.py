"""Phase 13 — durable history + checkpoints. 'Restart' = brand-new RunManager, graph and DB connections
pointed at the same files. MOCK fixtures, no API calls."""
import os
import sqlite3
import uuid

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from app.api.run_manager import RunManager
from app.graph.builder import build_graph
from app.graph.state import initial_state
from app.models import ProspectInput
from app.storage.base import RunRecord
from app.storage.sqlite_store import SQLiteRunStore


class SyncExecutor:
    def submit(self, fn, *args):
        fn(*args)

    def shutdown(self, **kw):
        pass


def _manager(tmp_path):
    saver = SqliteSaver(sqlite3.connect(tmp_path / "checkpoints.sqlite", check_same_thread=False))
    return RunManager(build_graph(saver), SQLiteRunStore(tmp_path / "app.sqlite"), executor=SyncExecutor())


def _rec(run_id, created, **kw):
    return RunRecord(run_id=run_id, prospect_name="P", company="C", title="T", prospect={}, created_at=created, **kw)


def test_sqlite_store_crud_and_order(tmp_path):
    store = SQLiteRunStore(tmp_path / "app.sqlite")
    store.create(_rec("old", "2026-11-01T10:00:00+00:00"))
    store.create(_rec("new", "2026-11-02T10:00:00+00:00"))
    store.update("old", status="approved", draft_status="approved", snapshot={"usage": {"groq_calls": 3}})
    store.update("missing", status="approved")  # no-op, no error
    assert [r.run_id for r in store.list()] == ["new", "old"]
    old = store.get("old")
    assert old.status == "approved" and old.snapshot["usage"]["groq_calls"] == 3 and old.updated_at > old.created_at
    assert store.get("missing") is None
    # survives a new connection
    assert SQLiteRunStore(tmp_path / "app.sqlite").get("old").status == "approved"


def test_paused_run_and_history_survive_restart(fakes, tmp_path):
    _, _, fx = fakes("happy_path")
    first = _manager(tmp_path)
    run_id = first.start(ProspectInput.model_validate(fx["prospect"]))
    assert first.detail(run_id)["status"] == "awaiting_review"
    del first  # "server stops"

    second = _manager(tmp_path)  # "server starts": new graph, new connections, same files
    second.mark_stale_runs()
    d = second.detail(run_id)
    assert d["status"] == "awaiting_review" and d["pending"]["type"] == "review"
    assert d["snapshot"]["draft"]["subject"] and d["snapshot"]["evidence"]
    assert [r.run_id for r in second.store.list()] == [run_id]
    second.resume(run_id, "review", {"action": "approve"})
    assert second.detail(run_id)["status"] == "approved"
    assert _manager(tmp_path).store.get(run_id).draft_status == "approved"  # decision persisted too


def test_run_interrupted_mid_flight_becomes_stale_and_retry_resumes(fakes, tmp_path):
    _, _, fx = fakes("happy_path")
    first = _manager(tmp_path)
    run_id = first.start(ProspectInput.model_validate(fx["prospect"]))
    first.store.update(run_id, status="running")  # simulate the server dying while the run was working
    second = _manager(tmp_path)
    second.mark_stale_runs()
    rec = second.store.get(run_id)
    assert rec.status == "stale" and "Retry" in rec.error
    second.retry(run_id)  # continues from the last checkpoint
    assert second.detail(run_id)["status"] == "awaiting_review"


@pytest.mark.integration
def test_postgres_checkpoints_survive_restart(fakes):
    """Real Neon Postgres (free tier). Uses MOCK research; cleans up its own thread."""
    from app.config import get_settings
    from app.graph.checkpoint import make_checkpointer

    _, _, fx = fakes("happy_path")
    s = get_settings().model_copy(update={"checkpoint_backend": "postgres"})
    if not (s.database_url and s.database_url.get_secret_value().strip()):
        pytest.skip("DATABASE_URL is empty")
    thread = f"test-{uuid.uuid4().hex[:10]}"
    config = {"configurable": {"thread_id": thread}, "recursion_limit": 60}
    saver1 = make_checkpointer(s)
    try:
        g1 = build_graph(saver1)
        list(g1.stream(initial_state(thread, fx["prospect"]), config, stream_mode="updates"))
        assert g1.get_state(config).interrupts[0].value["type"] == "review"

        saver2 = make_checkpointer(s)  # new pool = "restart"
        g2 = build_graph(saver2)
        assert g2.get_state(config).interrupts[0].value["type"] == "review"
        list(g2.stream(Command(resume={"action": "approve"}), config, stream_mode="updates"))
        assert g2.get_state(config).values["status"] == "approved"
    finally:
        saver1.delete_thread(thread)


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("FIRESTORE_EMULATOR_HOST"), reason="Firestore emulator not running")
def test_firestore_store_against_emulator():
    from app.storage.firestore_store import FirestoreRunStore

    store = FirestoreRunStore("demo-outreach", collection=f"runs-test-{uuid.uuid4().hex[:6]}")
    store.create(_rec("a", "2026-11-01T10:00:00+00:00"))
    store.create(_rec("b", "2026-11-02T10:00:00+00:00"))
    store.update("a", status="approved")
    assert [r.run_id for r in store.list()] == ["b", "a"] and store.get("a").status == "approved"
