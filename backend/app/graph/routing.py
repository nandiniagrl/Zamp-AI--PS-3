"""Pure routing functions (no side effects). Every loop in the graph is bounded by these limits."""
from langgraph.graph import END

MAX_REVISIONS = 2  # automatic quality revisions → at most 3 drafts per round
MAX_BROADEN = 1  # automatic broadened searches when no usable hook is found
MAX_CONTEXT_ROUNDS = 1  # extra research rounds driven by user-supplied context
RESEARCH_NODES = ["research_person", "research_company", "research_hiring"]


def route_after_resolve(state) -> str | list[str]:
    """Edge Case A: ambiguous identity → pause for the user; otherwise fan out to the 3 research branches."""
    return "identity_clarify" if state["identity"]["status"] == "ambiguous" else RESEARCH_NODES


def route_after_identity(state) -> str | list[str]:
    return END if state.get("status") == "aborted" else RESEARCH_NODES


def route_after_rank(state) -> str:
    """Edge Case B: no usable hook → broaden once (plus once per user-context round) → then ask the user.
    (Phase 9C adds the sensitive-only branch.)"""
    if any(r["eligible_for_hook"] for r in state.get("ranked", [])):
        return "draft_email"
    if state.get("broaden_attempts", 0) < MAX_BROADEN + state.get("context_rounds", 0):
        return "broaden_research"
    return "insufficient_evidence"


def route_after_quality(state) -> str:
    # Phase 10 replaces "finalize_draft" with "human_review"
    return "draft_email" if state.get("pending_feedback") else "finalize_draft"
