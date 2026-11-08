from app.config import Settings


def make_store(s: Settings):
    """Pick the RunStore implementation from STORAGE_BACKEND (memory now; sqlite/firestore in Phase 13)."""
    if s.storage_backend == "memory":
        from app.storage.memory_store import MemoryRunStore

        return MemoryRunStore()
    raise ValueError(f"Unsupported STORAGE_BACKEND={s.storage_backend!r} (sqlite/firestore are added in Phase 13)")
