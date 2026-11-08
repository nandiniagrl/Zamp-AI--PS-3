"""In-memory RunStore (Phase 11). Lost on restart — Phase 13 adds SQLite (local) and Firestore (cloud)."""
import threading

from app.storage.base import RunRecord, now_iso


class MemoryRunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._lock = threading.Lock()

    def create(self, rec: RunRecord) -> None:
        with self._lock:
            self._runs[rec.run_id] = rec

    def update(self, run_id: str, **fields) -> None:
        with self._lock:
            rec = self._runs.get(run_id)
            if rec is not None:
                self._runs[run_id] = rec.model_copy(update={**fields, "updated_at": now_iso()})

    def get(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def list(self, limit: int = 50) -> list[RunRecord]:
        with self._lock:
            return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)[:limit]
