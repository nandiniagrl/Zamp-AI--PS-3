"""SQLite RunStore — local, durable, zero setup (backend/.data/app.sqlite). One row per run, JSON body."""
import json
import sqlite3
import threading
from pathlib import Path

from app.storage.base import RunRecord, now_iso


class SQLiteRunStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()  # one writer at a time; RunManager persists from worker threads
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, data TEXT NOT NULL)"
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS runs_created ON runs(created_at DESC)")
            self._conn.commit()

    def create(self, rec: RunRecord) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO runs (run_id, created_at, data) VALUES (?, ?, ?)", (rec.run_id, rec.created_at, rec.model_dump_json())
            )
            self._conn.commit()

    def update(self, run_id: str, **fields) -> None:
        with self._lock:
            row = self._conn.execute("SELECT data FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                return
            data = json.loads(row[0]) | fields | {"updated_at": now_iso()}
            self._conn.execute("UPDATE runs SET data = ? WHERE run_id = ?", (RunRecord.model_validate(data).model_dump_json(), run_id))
            self._conn.commit()

    def get(self, run_id: str) -> RunRecord | None:
        with self._lock:
            row = self._conn.execute("SELECT data FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return RunRecord.model_validate_json(row[0]) if row else None

    def list(self, limit: int = 50) -> list[RunRecord]:
        with self._lock:
            rows = self._conn.execute("SELECT data FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [RunRecord.model_validate_json(r[0]) for r in rows]
