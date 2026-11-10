from app.config import Settings


def make_store(s: Settings):
    """Pick the RunStore from STORAGE_BACKEND: memory (tests), sqlite (local default), firestore (cloud)."""
    if s.storage_backend == "memory":
        from app.storage.memory_store import MemoryRunStore

        return MemoryRunStore()
    if s.storage_backend == "sqlite":
        from app.storage.sqlite_store import SQLiteRunStore

        return SQLiteRunStore(s.data_dir / "app.sqlite")
    if s.storage_backend == "firestore":
        from app.storage.firestore_store import FirestoreRunStore

        return FirestoreRunStore(s.gcp_project)
    raise ValueError(f"Unsupported STORAGE_BACKEND={s.storage_backend!r} (use memory, sqlite or firestore)")
