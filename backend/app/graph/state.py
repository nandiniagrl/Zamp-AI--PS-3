"""LangGraph state. Values are plain JSON (dict/list/str) so checkpoints serialise safely;
nodes re-validate with Pydantic on read. Annotated fields use reducers so parallel branches can append."""
import operator
from typing import Annotated, TypedDict


def merge_usage(a: dict | None, b: dict | None) -> dict:
    a, b = a or {}, b or {}
    return {k: a.get(k, 0) + b.get(k, 0) for k in {*a, *b}}


class OutreachState(TypedDict, total=False):
    run_id: str
    prospect: dict  # ProspectInput
    tone: str
    status: str
    identity: dict  # IdentityResolution
    research: Annotated[list[dict], operator.add]  # ResearchRecord, appended by parallel branches
    research_errors: Annotated[list[str], operator.add]
    processed_record_ids: list[str]
    evidence: list[dict]
    conflicts: list[dict]
    ranked: list[dict]
    top_explanation: str
    selected_evidence_id: str | None
    draft: dict | None
    final_draft: dict | None
    quality: dict | None
    pending_feedback: list[str]
    revision_count: int
    regenerations: int
    broaden_attempts: int
    targeted_attempts: int
    context_rounds: int
    user_context: str | None
    instructions: str | None
    edge_cases: Annotated[list[dict], operator.add]
    progress: Annotated[list[dict], operator.add]
    review_log: Annotated[list[dict], operator.add]
    usage: Annotated[dict, merge_usage]


def initial_state(run_id: str, prospect: dict) -> OutreachState:
    return OutreachState(
        run_id=run_id, prospect=prospect, tone=prospect.get("tone", "professional"), status="researching",
        research=[], research_errors=[], processed_record_ids=[], evidence=[], conflicts=[], ranked=[],
        edge_cases=[], progress=[], review_log=[], usage={}, revision_count=0, regenerations=0,
        broaden_attempts=0, targeted_attempts=0, context_rounds=0, pending_feedback=[],
    )
