"""Pure routing functions (no side effects). Every loop in the graph is bounded by these limits."""
from langgraph.graph import END

MAX_REVISIONS = 2  # automatic quality revisions → at most 3 drafts per round
MAX_BROADEN = 1  # automatic broadened searches when no usable hook is found
MAX_CONTEXT_ROUNDS = 1  # extra research rounds driven by user-supplied context
MAX_TARGETED = 1  # targeted verification searches for conflicting evidence
IDENTITY_CONFLICT_TYPES = {"person_role", "employer"}
RESEARCH_NODES = ["research_person", "research_company", "research_hiring"]


def route_after_resolve(state) -> str | list[str]:
    """Edge Case A: ambiguous identity → pause for the user; otherwise fan out to the 3 research branches."""
    return "identity_clarify" if state["identity"]["status"] == "ambiguous" else RESEARCH_NODES


def route_after_identity(state) -> str | list[str]:
    return END if state.get("status") == "aborted" else RESEARCH_NODES


def route_after_verify(state) -> str:
    """Edge Case D: unresolved conflict → one targeted verification round. Still unresolved:
    identity facts (role/employer) → ask the user; business facts were already excluded by verify_evidence."""
    unresolved = [c for c in state.get("conflicts", []) if c["status"] == "unresolved"]
    if unresolved and state.get("targeted_attempts", 0) < MAX_TARGETED:
        return "targeted_verification"
    if any(c["claim_type"] in IDENTITY_CONFLICT_TYPES for c in unresolved):
        return "conflict_review"
    return "rank_signals"


def route_after_rank(state) -> str:
    """Edge Cases B & C. A sensitive signal is never eligible as a hook, so if one ranks top the best
    non-sensitive alternative is used. No usable hook → broaden once (plus once per user-context round);
    still nothing → ask the user: 'sensitive_judgment' if only sensitive signals exist, else 'insufficient_evidence'."""
    ranked = state.get("ranked", [])
    if any(r["eligible_for_hook"] for r in ranked):
        return "draft_email"
    if state.get("broaden_attempts", 0) < MAX_BROADEN + state.get("context_rounds", 0):
        return "broaden_research"
    if any(r["is_sensitive"] for r in ranked):
        return "sensitive_judgment"
    return "insufficient_evidence"


def route_after_quality(state) -> str:
    # Phase 10 replaces "finalize_draft" with "human_review"
    return "draft_email" if state.get("pending_feedback") else "finalize_draft"
