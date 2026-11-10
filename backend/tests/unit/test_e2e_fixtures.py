"""Phase 15 — every MOCK scenario end-to-end through the HTTP API (real FastAPI app + real graph).

For each fixture: the run pauses where it should, records the right edge cases, every claim in any draft is
backed by verified, non-sensitive evidence whose quote is in the retrieved text, and a run only ever
reaches 'approved' through a human 'review' decision. Nothing can be sent.
"""
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from app.api.main import create_app
from app.api.run_manager import RunManager
from app.graph.builder import build_graph
from app.storage.memory_store import MemoryRunStore
from scripts.evaluate import audit_claims


class SyncExecutor:
    def submit(self, fn, *args):
        fn(*args)

    def shutdown(self, **kw):
        pass


def _answer(pending: dict) -> dict:
    """What a reviewer does at each non-review pause in these scenarios."""
    kind = pending["type"]
    if kind == "identity":
        return {"candidate_id": pending["candidates"][-1]["id"]}
    if kind == "conflict":
        return {"resolutions": {c["id"]: "exclude" for c in pending["conflicts"]}}
    return {"action": "abstain"}  # insufficient / sensitive: never fabricate a hook


# fixture → (first pause or terminal status, edge cases expected, final status after the reviewer acts)
SCENARIOS = {
    "happy_path": ("awaiting_review", set(), "approved"),
    "identity_ambiguous": ("awaiting_identity", {"A"}, None),
    "no_signals": ("awaiting_context", {"B"}, "insufficient"),
    "sensitive_news": ("awaiting_review", {"C"}, "approved"),
    "sensitive_only": ("awaiting_judgment", {"B", "C"}, "abstained"),
    "conflicting_role": ("awaiting_review", {"D"}, "approved"),
    "conflicting_unresolved": ("awaiting_conflict", {"D"}, None),
    "conflicting_funding": ("awaiting_review", {"D"}, "approved"),
}


@pytest.mark.parametrize("fixture", list(SCENARIOS))
def test_scenario_end_to_end(fakes, fixture):
    first, edges, final = SCENARIOS[fixture]
    _, _, fx = fakes(fixture)
    manager = RunManager(build_graph(InMemorySaver()), MemoryRunStore(), executor=SyncExecutor())
    with TestClient(create_app(manager)) as client:
        run_id = client.post("/runs", json=fx["prospect"]).json()["run_id"]
        run = client.get(f"/runs/{run_id}").json()
        assert run["status"] == first
        assert {e["case"] for e in run["snapshot"]["edge_cases"]} >= edges

        decisions = []
        for _ in range(6):  # answer pauses until the run ends or reaches human review
            run = client.get(f"/runs/{run_id}").json()
            pending = run["pending"]
            assert run["status"] != "approved" or "review" in decisions, "approved without a human review decision"
            if pending is None:
                break
            state = manager.graph.get_state(manager._config(run_id)).values
            audit = audit_claims(state)
            assert audit["supported"] == audit["claims"], audit["rows"]  # 100% claim audit on every draft
            if pending["type"] == "review":
                decisions.append("review")
                r = client.post(f"/runs/{run_id}/resume", json={"type": "review", "value": {"action": "approve"}})
            else:
                decisions.append(pending["type"])
                r = client.post(f"/runs/{run_id}/resume", json={"type": pending["type"], "value": _answer(pending)})
            assert r.status_code == 202, r.text

        run = client.get(f"/runs/{run_id}").json()
        assert run["pending"] is None and not run["is_active"]
        if final:
            assert run["status"] == final
        else:
            assert run["status"] in {"approved", "insufficient", "abstained", "aborted"}
        if run["status"] == "approved":
            assert decisions[-1] == "review" and run["snapshot"]["final_draft"]["body"]
        else:
            assert not run["snapshot"].get("final_draft")


def test_no_route_can_send_email(fakes):
    fakes("happy_path")
    app = create_app(RunManager(build_graph(InMemorySaver()), MemoryRunStore(), executor=SyncExecutor()))
    paths = {getattr(r, "path", "") for r in app.routes}
    assert not any(word in p.lower() for p in paths for word in ("send", "mail", "smtp"))
