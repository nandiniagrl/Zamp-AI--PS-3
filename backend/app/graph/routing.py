"""Pure routing functions (no side effects). Every loop in the graph is bounded by these limits."""
from langgraph.graph import END

MAX_REVISIONS = 2  # automatic quality revisions → at most 3 drafts per round
RESEARCH_NODES = ["research_person", "research_company", "research_hiring"]


def route_after_resolve(state) -> str | list[str]:
    """Edge Case A: ambiguous identity → pause for the user; otherwise fan out to the 3 research branches."""
    return "identity_clarify" if state["identity"]["status"] == "ambiguous" else RESEARCH_NODES


def route_after_identity(state) -> str | list[str]:
    return END if state.get("status") == "aborted" else RESEARCH_NODES


def route_after_rank(state) -> str:
    # Phase 9B/9C add: broaden_research / insufficient_evidence / sensitive_judgment
    if any(r["eligible_for_hook"] for r in state.get("ranked", [])):
        return "draft_email"
    return END


def route_after_quality(state) -> str:
    # Phase 10 replaces "finalize_draft" with "human_review"
    return "draft_email" if state.get("pending_feedback") else "finalize_draft"
