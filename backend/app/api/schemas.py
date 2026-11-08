"""API request/response models."""
from typing import Literal

from pydantic import BaseModel, Field

from app.models import ConflictDecision, ContextDecision, IdentityChoice, ReviewDecision

InterruptType = Literal["identity", "conflict", "insufficient", "sensitive", "review"]

# Which payload model validates the answer to each kind of pause.
RESUME_MODELS = {"identity": IdentityChoice, "conflict": ConflictDecision, "insufficient": ContextDecision,
                 "sensitive": ContextDecision, "review": ReviewDecision}
STATUS_FOR_INTERRUPT = {"identity": "awaiting_identity", "conflict": "awaiting_conflict",
                        "insufficient": "awaiting_context", "sensitive": "awaiting_judgment",
                        "review": "awaiting_review"}


class RunCreated(BaseModel):
    run_id: str
    status: str


class ResumeRequest(BaseModel):
    type: InterruptType = Field(description="Must match the run's pending pause type")
    value: dict = Field(description="Answer payload, e.g. {'action': 'approve'} for a review pause",
                        examples=[{"action": "approve"}])


class RunSummary(BaseModel):
    run_id: str
    prospect_name: str
    company: str
    title: str
    status: str
    draft_status: str
    created_at: str
    updated_at: str
    error: str | None = None
