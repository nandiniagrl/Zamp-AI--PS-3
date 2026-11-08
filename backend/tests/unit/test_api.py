"""Phase 11 API tests: real FastAPI app + real graph, with MOCK Tavily/Groq and a synchronous executor."""
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from app.api.main import create_app
from app.api.run_manager import RunManager
from app.graph.builder import build_graph
from app.storage.memory_store import MemoryRunStore


class SyncExecutor:
    """Runs submitted work immediately so tests are deterministic."""

    def submit(self, fn, *args):
        fn(*args)

    def shutdown(self, **kw):
        pass


@pytest.fixture
def client_for(fakes):
    def make(fixture: str):
        _, _, fx = fakes(fixture)
        manager = RunManager(build_graph(InMemorySaver()), MemoryRunStore(), executor=SyncExecutor())
        client = TestClient(create_app(manager))
        client.__enter__()  # run lifespan
        return client, fx
    return make


def test_health(client_for):
    client, _ = client_for("happy_path")
    assert client.get("/health").json() == {"status": "ok"}


def test_full_flow_create_poll_review_approve(client_for):
    client, fx = client_for("happy_path")
    r = client.post("/runs", json=fx["prospect"])
    assert r.status_code == 202
    run_id = r.json()["run_id"]
    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "awaiting_review" and run["draft_status"] == "pending"
    assert run["pending"]["type"] == "review" and run["snapshot"]["draft"]["subject"]
    assert run["snapshot"]["evidence"] and run["snapshot"]["ranked"] and run["snapshot"]["progress"]
    r = client.post(f"/runs/{run_id}/resume", json={"type": "review", "value": {"action": "approve"}})
    assert r.status_code == 202
    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "approved" and run["draft_status"] == "approved" and run["pending"] is None
    assert run["snapshot"]["final_draft"]["body"] == run["snapshot"]["draft"]["body"]


def test_history_lists_runs(client_for):
    client, fx = client_for("happy_path")
    ids = [client.post("/runs", json=fx["prospect"]).json()["run_id"] for _ in range(2)]
    rows = client.get("/runs").json()
    assert {r["run_id"] for r in rows} == set(ids)
    assert set(rows[0]) >= {"prospect_name", "company", "status", "draft_status", "created_at"}
    assert "snapshot" not in rows[0]


def test_identity_pause_and_resume(client_for):
    client, fx = client_for("identity_ambiguous")
    run_id = client.post("/runs", json=fx["prospect"]).json()["run_id"]
    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "awaiting_identity" and run["pending"]["type"] == "identity"
    bad = client.post(f"/runs/{run_id}/resume", json={"type": "identity", "value": {"candidate_id": "c99"}})
    assert bad.status_code == 422
    ok = client.post(f"/runs/{run_id}/resume", json={"type": "identity", "value": {"abort": True}})
    assert ok.status_code == 202 and client.get(f"/runs/{run_id}").json()["status"] == "aborted"


def test_error_codes(client_for):
    client, fx = client_for("happy_path")
    assert client.get("/runs/nope").status_code == 404
    assert client.post("/runs/nope/resume", json={"type": "review", "value": {"action": "approve"}}).status_code == 404
    assert client.post("/runs", json={"name": "x"}).status_code == 422                          # invalid prospect
    run_id = client.post("/runs", json=fx["prospect"]).json()["run_id"]
    wrong = client.post(f"/runs/{run_id}/resume", json={"type": "identity", "value": {"abort": True}})
    assert wrong.status_code == 409 and "waiting for 'review'" in wrong.json()["detail"]
    bad = client.post(f"/runs/{run_id}/resume", json={"type": "review", "value": {"action": "send"}})
    assert bad.status_code == 422                                                              # no "send" action
    assert client.post(f"/runs/{run_id}/retry").status_code == 409                             # not failed


def test_failed_run_reports_safe_error_and_can_retry(client_for, monkeypatch):
    client, fx = client_for("happy_path")
    from app.graph import nodes
    real = nodes.rank

    def boom(*a, **k):
        raise RuntimeError("Groq exploded with key gsk_SECRET1234567890")
    monkeypatch.setattr(nodes, "rank", boom)
    run_id = client.post("/runs", json=fx["prospect"]).json()["run_id"]
    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "failed" and "gsk_" not in run["error"] and "[REDACTED]" in run["error"]
    monkeypatch.setattr(nodes, "rank", real)
    assert client.post(f"/runs/{run_id}/retry").status_code == 202
    assert client.get(f"/runs/{run_id}").json()["status"] == "awaiting_review"   # resumed from checkpoint


def test_no_send_route_exists(client_for):
    client, _ = client_for("happy_path")
    paths = [getattr(r, "path", "") for r in client.app.routes]
    assert not any("send" in p or "email" in p for p in paths)
    assert "/docs" in paths and "/openapi.json" in paths


def test_usage_endpoint_sums_runs(client_for):
    client, fx = client_for("happy_path")
    client.post("/runs", json=fx["prospect"])
    usage = client.get("/usage").json()
    assert usage["groq_calls"] >= 1 and usage["tavily_credits"] >= 1
