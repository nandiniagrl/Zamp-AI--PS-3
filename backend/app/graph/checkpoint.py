"""Checkpointer factory. Checkpoints let a paused run (interrupt) survive restarts and resume by thread_id.

memory   : InMemorySaver — tests and throwaway scripts (lost when the process exits)
sqlite   : SqliteSaver   — local default; durable file at backend/.data/checkpoints.sqlite
postgres : PostgresSaver — cloud; free Neon Postgres via DATABASE_URL (Cloud Run disks are ephemeral)
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

    if s.checkpoint_backend == "postgres":
        if s.database_url is None or not s.database_url.get_secret_value().strip():
            raise ValueError("CHECKPOINT_BACKEND=postgres needs DATABASE_URL (your Neon connection string) in backend/.env")
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        pool = ConnectionPool(
            s.database_url.get_secret_value(),
            min_size=1,
            max_size=4,
            open=True,
            # Neon's free compute suspends when idle and kills open connections. Test each connection
            # before handing it out (a dead one is replaced, not used) and drop idle ones early.
            check=ConnectionPool.check_connection,
            max_idle=120,
            # Required by PostgresSaver; prepare_threshold=0 also keeps it safe behind Neon's pgbouncer pooler.
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        )
        saver = PostgresSaver(pool)
        saver.setup()  # idempotent: creates/migrates the checkpoint tables (must be called explicitly)
        return saver

    raise ValueError(f"Unsupported CHECKPOINT_BACKEND={s.checkpoint_backend!r} (use memory, sqlite or postgres)")
