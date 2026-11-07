"""Checkpointer factory. Checkpoints let a paused run (interrupt) survive and resume by thread_id.

memory   : InMemorySaver — tests and one-off scripts (lost when the process exits)
sqlite   : SqliteSaver   — local development; survives restarts (backend/.data/checkpoints.sqlite)
postgres : PostgresSaver — cloud (Phase 13/14, free Neon Postgres)
"""
import sqlite3
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from app.config import Settings


def make_checkpointer(s: Settings, sqlite_path: Path | None = None):
    if s.checkpoint_backend == "memory":
        return InMemorySaver()
    if s.checkpoint_backend == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver

        path = sqlite_path or (s.data_dir / "checkpoints.sqlite")
        path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False is safe: SqliteSaver serialises access with an internal lock (per its docs)
        return SqliteSaver(sqlite3.connect(path, check_same_thread=False))
    raise ValueError(f"Unsupported CHECKPOINT_BACKEND={s.checkpoint_backend!r} (postgres is added in Phase 13)")
