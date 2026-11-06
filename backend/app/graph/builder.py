"""Wires the nodes into a LangGraph StateGraph."""
from langgraph.graph import END, START, StateGraph

from app.graph import nodes as n
from app.graph.routing import (RESEARCH_NODES, route_after_identity, route_after_quality, route_after_rank,
                               route_after_resolve)
from app.graph.state import OutreachState


def build_graph(checkpointer=None):
    g = StateGraph(OutreachState)
    for name in ["resolve_prospect", "identity_clarify", *RESEARCH_NODES, "verify_evidence", "rank_signals",
                 "draft_email", "quality_check", "finalize_draft"]:
        g.add_node(name, getattr(n, name))

    g.add_edge(START, "resolve_prospect")
    g.add_conditional_edges("resolve_prospect", route_after_resolve, ["identity_clarify", *RESEARCH_NODES])  # A / fan-out
    g.add_conditional_edges("identity_clarify", route_after_identity, [*RESEARCH_NODES, END])
    g.add_edge(RESEARCH_NODES, "verify_evidence")  # fan-in: waits for all three branches
    g.add_edge("verify_evidence", "rank_signals")
    g.add_conditional_edges("rank_signals", route_after_rank, ["draft_email", END])
    g.add_edge("draft_email", "quality_check")
    g.add_conditional_edges("quality_check", route_after_quality, ["draft_email", "finalize_draft"])  # bounded loop
    g.add_edge("finalize_draft", END)
    return g.compile(checkpointer=checkpointer)
