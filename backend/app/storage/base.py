"""Run records (history / dashboard list). The LangGraph checkpointer stores workflow state;
this store keeps a searchable summary + snapshot so history works even without loading checkpoints."""
from datetime import datetime, timezone
from typing import Protocol

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunRecord(BaseModel):
    run_id: str
    prospect_name: str
    company: str
    title: str
    status: str = "running"
    draft_status: str = "none"  # none | pending | approved | rejected
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    error: str | None = None
    prospect: dict
    snapshot: dict = Field(default_factory=dict)  # evidence, ranked, draft, quality, edge_cases, usage, …


class RunStore(Protocol):
    def create(self, rec: RunRecord) -> None: ...
    def update(self, run_id: str, **fields) -> None: ...
    def get(self, run_id: str) -> RunRecord | None: ...
    def list(self, limit: int = 50) -> list[RunRecord]: ...
