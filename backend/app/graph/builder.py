"""Wires the nodes into a LangGraph StateGraph."""
from langgraph.graph import END, START, StateGraph

from app.graph import nodes as n
from app.graph.routing import (RESEARCH_NODES, route_after_identity, route_after_quality, route_after_rank,
                               route_after_resolve, route_after_verify)
from app.graph.state import OutreachState


def build_graph(checkpointer=None):
    g = StateGraph(OutreachState)
    for name in ["resolve_prospect", "identity_clarify", *RESEARCH_NODES, "verify_evidence",
                 "targeted_verification", "conflict_review", "rank_signals",
                 "broaden_research", "insufficient_evidence", "sensitive_judgment",
                 "draft_email", "quality_check", "human_review"]:
        g.add_node(name, getattr(n, name))

    g.add_edge(START, "resolve_prospect")
    g.add_conditional_edges("resolve_prospect", route_after_resolve, ["identity_clarify", *RESEARCH_NODES])  # A / fan-out
    g.add_conditional_edges("identity_clarify", route_after_identity, [*RESEARCH_NODES, END])
    g.add_edge(RESEARCH_NODES, "verify_evidence")  # fan-in: waits for all three branches
    g.add_conditional_edges("verify_evidence", route_after_verify,
                            ["targeted_verification", "conflict_review", "rank_signals"])  # Edge Case D
    g.add_edge("targeted_verification", "verify_evidence")
    g.add_conditional_edges("rank_signals", route_after_rank,
                            ["draft_email", "broaden_research", "insufficient_evidence", "sensitive_judgment"])  # B / C
    g.add_edge("broaden_research", "verify_evidence")
    # conflict_review, insufficient_evidence and sensitive_judgment route themselves via Command(goto=...)
    g.add_edge("draft_email", "quality_check")
    g.add_conditional_edges("quality_check", route_after_quality, ["draft_email", "human_review"])  # bounded loop
    # human_review routes itself via Command(goto=END | draft_email | quality_check | human_review)
    return g.compile(checkpointer=checkpointer)
