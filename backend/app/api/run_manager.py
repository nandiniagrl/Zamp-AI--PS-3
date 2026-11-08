"""Runs LangGraph workflows in background threads so HTTP requests return immediately.

The browser only polls GET /runs/{id}; closing the browser does not stop or lose a run.
thread_id == run_id, so every resume continues the same checkpointed workflow.
"""
import logging
import threading
import uuid
from concurrent.futures import Executor, ThreadPoolExecutor

from langgraph.types import Command

from app.api.schemas import RESUME_MODELS, STATUS_FOR_INTERRUPT
from app.graph.state import initial_state
from app.logging_setup import redact
from app.models import ProspectInput
from app.storage.base import RunRecord, RunStore

log = logging.getLogger(__name__)
TERMINAL = {"approved", "rejected", "insufficient", "abstained", "aborted", "failed"}
SNAPSHOT_KEYS = ["identity", "evidence", "conflicts", "ranked", "top_explanation", "draft", "final_draft", "quality",
                 "edge_cases", "progress", "usage", "research_errors", "review_log", "selected_evidence_id"]
DRAFT_STATUS = {"approved": "approved", "rejected": "rejected", "awaiting_review": "pending"}


class RunNotFound(Exception):
    pass


class RunConflictError(Exception):
    """The request does not fit the run's current state (e.g. not paused, or already executing)."""


class RunManager:
    def __init__(self, graph, store: RunStore, executor: Executor | None = None):
        self.graph, self.store = graph, store
        self.executor = executor or ThreadPoolExecutor(max_workers=4, thread_name_prefix="run")
        self._active: set[str] = set()
        self._lock = threading.Lock()

    @staticmethod
    def _config(run_id: str) -> dict:
        return {"configurable": {"thread_id": run_id}, "recursion_limit": 60}

    # ------------------------------------------------------------------ commands
    def start(self, prospect: ProspectInput) -> str:
        run_id = uuid.uuid4().hex[:16]
        data = prospect.model_dump(mode="json")
        self.store.create(RunRecord(run_id=run_id, prospect_name=prospect.name, company=prospect.company,
                                    title=prospect.title, prospect=data, status="running"))
        self._submit(run_id, initial_state(run_id, data))
        return run_id

    def resume(self, run_id: str, kind: str, value: dict) -> None:
        if self.store.get(run_id) is None:
            raise RunNotFound(run_id)
        if run_id in self._active:
            raise RunConflictError("Run is still executing; wait until it pauses.")
        pending = self.pending_interrupt(run_id)
        if pending is None:
            raise RunConflictError("Run is not waiting for any input.")
        if pending["type"] != kind:
            raise RunConflictError(f"Run is waiting for '{pending['type']}', not '{kind}'.")
        answer = RESUME_MODELS[kind].model_validate(value)  # ValidationError → 422
        if kind == "review" and answer.action == "choose_signal":
            if answer.evidence_id not in {a["evidence_id"] for a in pending.get("alternatives", [])}:
                raise ValueError("evidence_id is not one of the eligible alternative signals")
        if kind == "identity" and answer.candidate_id:
            if answer.candidate_id not in {c["id"] for c in pending.get("candidates", [])}:
                raise ValueError("candidate_id is not one of the offered candidates")
        self.store.update(run_id, status="running", error=None)
        self._submit(run_id, Command(resume=answer.model_dump(mode="json", exclude_none=True)))

    def retry(self, run_id: str) -> None:
        """Continue a failed/stale run from its last checkpoint (completed steps are not re-run)."""
        rec = self.store.get(run_id)
        if rec is None:
            raise RunNotFound(run_id)
        if rec.status not in {"failed", "stale"}:
            raise RunConflictError(f"Only failed or stale runs can be retried (status: {rec.status}).")
        self.store.update(run_id, status="running", error=None)
        self._submit(run_id, None)

    # ------------------------------------------------------------------ execution
    def _submit(self, run_id: str, payload) -> None:
        with self._lock:
            if run_id in self._active:
                raise RunConflictError("Run is already executing.")
            self._active.add(run_id)
        self.executor.submit(self._drive, run_id, payload)

    def _drive(self, run_id: str, payload) -> None:
        try:
            for _ in self.graph.stream(payload, self._config(run_id), stream_mode="updates"):
                self._persist(run_id)  # live progress for polling clients
            self._persist(run_id)
        except Exception as exc:  # never crash the server; surface a safe message
            log.exception("Run %s failed", run_id)
            self.store.update(run_id, status="failed", error=redact(f"{type(exc).__name__}: {exc}")[:400])
        finally:
            with self._lock:
                self._active.discard(run_id)

    def _persist(self, run_id: str) -> None:
        snap = self.graph.get_state(self._config(run_id))
        values = snap.values or {}
        if snap.interrupts:
            status = STATUS_FOR_INTERRUPT[snap.interrupts[0].value["type"]]
        elif snap.next:
            status = "running"
        else:
            status = values.get("status") if values.get("status") in TERMINAL else "completed"
        draft_status = DRAFT_STATUS.get(status, "pending" if values.get("draft") else "none")
        fields = {"status": status, "draft_status": draft_status,
                  "snapshot": {k: values.get(k) for k in SNAPSHOT_KEYS}}
        if values.get("prospect"):  # identity choice may update company/title
            p = values["prospect"]
            fields |= {"prospect": p, "prospect_name": p["name"], "company": p["company"], "title": p["title"]}
        self.store.update(run_id, **fields)

    # ------------------------------------------------------------------ queries
    def pending_interrupt(self, run_id: str) -> dict | None:
        snap = self.graph.get_state(self._config(run_id))
        return snap.interrupts[0].value if snap.interrupts else None

    def detail(self, run_id: str) -> dict:
        rec = self.store.get(run_id)
        if rec is None:
            raise RunNotFound(run_id)
        try:
            pending = self.pending_interrupt(run_id) if run_id not in self._active else None
        except Exception:  # checkpoint missing → history still works from the snapshot
            pending = None
        return {**rec.model_dump(mode="json"), "pending": pending, "is_active": run_id in self._active}

    def mark_stale_runs(self) -> None:
        """On startup: runs that were mid-execution when the server stopped can be retried from checkpoint."""
        for rec in self.store.list(limit=500):
            if rec.status == "running":
                self.store.update(rec.run_id, status="stale", error="Server restarted while this run was working. Retry it.")

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=False)
