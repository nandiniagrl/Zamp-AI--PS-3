"""Graph nodes: thin adapters that re-validate state, call one module, and return JSON updates.
Each node appends a human-readable `progress` entry so every step is inspectable."""
from datetime import datetime, timezone

from typing import Literal

from langgraph.graph import END
from langgraph.types import Command, interrupt

from app.drafting.generator import generate_draft
from app.graph import routing
from app.identity import resolver
from app.models import (ContextDecision, Draft, Evidence, IdentityChoice, IdentityResolution, ProspectInput, RankedSignal,
                        ResearchRecord)
from app.quality.checker import check_draft
from app.ranking.ranker import rank_signals as rank
from app.research import pipeline, queries
from app.verification import verifier


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _p(state) -> ProspectInput:
    return ProspectInput.model_validate(state["prospect"])


def _progress(node: str, message: str) -> list[dict]:
    return [{"node": node, "message": message, "ts": _now()}]


def _dump(items) -> list[dict]:
    return [i.model_dump(mode="json") for i in items]


EDGE_TITLES = {"A": "Ambiguous prospect identity", "B": "Insufficient public signals",
               "C": "Sensitive company news", "D": "Conflicting or outdated evidence"}


def _edge(case: str, message: str, action: str) -> list[dict]:
    """An edge-case record shown to the user: what happened and what the agent did about it."""
    return [{"case": case, "title": EDGE_TITLES[case], "message": message, "action": action, "ts": _now()}]


# ---------------------------------------------------------------- identity (Edge Case A)
def resolve_prospect(state):
    res, usage = resolver.resolve_identity(_p(state))
    upd = {"identity": res.model_dump(mode="json"), "usage": usage, "status": "researching",
           "progress": _progress("resolve_prospect", f"[{res.status}] {res.explanation}")}
    if res.status == "ambiguous":
        upd |= {"status": "awaiting_identity",
                "edge_cases": _edge("A", res.explanation, "Paused for you to choose the correct person (no guessing).")}
    return upd


def identity_clarify(state):
    """Pauses the graph (LangGraph interrupt). Nothing before interrupt() has side effects, because the node
    re-runs from the top when resumed."""
    ident = IdentityResolution.model_validate(state["identity"])
    answer = interrupt({"type": "identity", "message": ident.explanation,
                        "candidates": _dump(ident.candidates),
                        "options": {"candidate_id": "pick one of the candidates",
                                    "company_only": "skip person research", "abort": "stop this run"}})
    choice = IdentityChoice.model_validate(answer)
    ident, prospect = resolver.apply_choice(ident, choice, _p(state))
    return {"identity": ident.model_dump(mode="json"), "prospect": prospect.model_dump(mode="json"),
            "status": "aborted" if choice.abort else "researching",
            "progress": _progress("identity_clarify", ident.explanation)}


# ---------------------------------------------------------------- research (3 parallel branches)
def _research_node(branch: str):
    def node(state):
        if branch == "person" and state["identity"]["status"] != "confirmed":
            return {"progress": _progress(f"research_{branch}",
                                          "Skipped: identity not confirmed (company-level research only).")}
        res = pipeline.run_branch(branch, _p(state))
        return {"research": _dump(res.records), "research_errors": res.errors, "usage": res.usage,
                "progress": _progress(f"research_{branch}", f"{len(res.records)} sources, {len(res.errors)} errors")}

    node.__name__ = f"research_{branch}"
    return node


research_person = _research_node("person")
research_company = _research_node("company")
research_hiring = _research_node("hiring")


# ---------------------------------------------------------------- verification
def verify_evidence(state):
    p = _p(state)
    done = set(state.get("processed_record_ids", []))
    records = pipeline.dedupe([ResearchRecord.model_validate(r) for r in state.get("research", [])])
    new = [r for r in records if r.id not in done]
    result = verifier.verify(p, new, prior=[Evidence.model_validate(e) for e in state.get("evidence", [])])
    counts = {s: sum(e.verification_status == s for e in result.evidence)
              for s in ("verified", "uncertain", "disputed", "rejected")}
    summary = ", ".join(f"{v} {k}" for k, v in counts.items())
    unresolved = sum(c.status == "unresolved" for c in result.conflicts)
    return {"evidence": _dump(result.evidence), "conflicts": _dump(result.conflicts),
            "processed_record_ids": sorted(done | {r.id for r in new}), "usage": result.usage,
            "research_errors": result.errors,
            "progress": _progress("verify_evidence", f"{summary}; {unresolved} unresolved conflicts")}


# ---------------------------------------------------------------- ranking
def rank_signals(state):
    result = rank(_p(state), [Evidence.model_validate(e) for e in state.get("evidence", [])])
    n_eligible = sum(r.eligible_for_hook for r in result.ranked)
    upd = {"ranked": _dump(result.ranked), "top_explanation": result.top_explanation, "usage": result.usage,
           "progress": _progress("rank_signals", f"{n_eligible} eligible of {len(result.ranked)} ranked")}
    return upd


# ---------------------------------------------------------------- Edge Case B: insufficient signals
def broaden_research(state):
    """Widen the search toward verified company context and role priorities (+ user context if given)."""
    p = _p(state)
    user_context = state.get("user_context")
    res = pipeline.run_queries("broadened", queries.broadened_queries(p, user_context))
    why = f"Searching again with your context: \"{user_context}\"." if user_context else \
        "Broadened search to verified company context and role-relevant priorities."
    return {"research": _dump(res.records), "research_errors": res.errors, "usage": res.usage,
            "broaden_attempts": state.get("broaden_attempts", 0) + 1, "status": "researching",
            "edge_cases": _edge("B", "No credible, specific, recent signal was usable as an outreach hook.", why),
            "progress": _progress("broaden_research", f"{len(res.records)} broadened sources")}


def _context_or_abstain(state, kind: str, payload: dict) -> Command:
    """Shared pause: user adds context (one bounded extra research round) or abstains. Never fabricates a hook."""
    can_add = state.get("context_rounds", 0) < routing.MAX_CONTEXT_ROUNDS
    decision = ContextDecision.model_validate(interrupt({**payload, "can_add_context": can_add}))
    if decision.action == "add_context" and decision.context and can_add:
        return Command(goto="broaden_research", update={
            "user_context": decision.context.strip(), "context_rounds": state.get("context_rounds", 0) + 1,
            "status": "researching", "progress": _progress(kind, f"Reviewer added context: {decision.context.strip()}")})
    final = "insufficient" if kind == "insufficient_evidence" else "abstained"
    return Command(goto=END, update={"status": final,
                                     "progress": _progress(kind, "Stopped without drafting — no fabricated hook.")})


def insufficient_evidence(state) -> Command[Literal["broaden_research", "__end__"]]:
    counts = {s: sum(e["verification_status"] == s for e in state.get("evidence", []))
              for s in ("verified", "uncertain", "rejected")}
    return _context_or_abstain(state, "insufficient_evidence", {
        "type": "insufficient",
        "message": "Insufficient verified research",
        "detail": ("No credible, specific signal could be verified, even after broadening the search "
                   f"({counts['verified']} verified, {counts['uncertain']} uncertain, {counts['rejected']} rejected claims). "
                   "Add context — e.g. a recent announcement, initiative or topic to look for — or stop."),
        "options": {"add_context": "provide context and search once more", "abstain": "stop without a draft"},
    })


# ---------------------------------------------------------------- drafting & quality
def _allowed(state, draft: Draft) -> dict[str, Evidence]:
    ev = {e["id"]: e for e in state["evidence"]}
    ids = [draft.hook_evidence_id, *draft.supporting_evidence_ids]
    return {i: Evidence.model_validate(ev[i]) for i in ids if i in ev}


def draft_email(state):
    p = _p(state)
    ev = {e["id"]: Evidence.model_validate(e) for e in state["evidence"]}
    eligible = [RankedSignal.model_validate(r) for r in state["ranked"] if r["eligible_for_hook"]]
    hook_id = state.get("selected_evidence_id") or eligible[0].evidence_id
    supporting = [ev[r.evidence_id] for r in eligible if r.evidence_id != hook_id][:1]
    version = (state.get("draft") or {}).get("version", 0) + 1
    draft, usage = generate_draft(p, ev[hook_id], supporting, tone=state.get("tone") or p.tone, version=version,
                                  feedback=state.get("pending_feedback") or None, instructions=state.get("instructions"))
    note = " (revision with quality feedback)" if state.get("pending_feedback") else ""
    return {"draft": draft.model_dump(mode="json"), "selected_evidence_id": hook_id, "pending_feedback": [],
            "status": "drafting", "usage": usage,
            "progress": _progress("draft_email", f"Draft v{version}, {draft.word_count} words{note}")}


def quality_check(state):
    draft = Draft.model_validate(state["draft"])
    report, usage = check_draft(draft, _p(state), _allowed(state, draft))
    revisions = state.get("revision_count", 0)
    upd = {"quality": report.model_dump(mode="json"), "usage": usage}
    if report.passed:
        msg = "passed"
    elif not report.needs_human and not draft.edited_by_human and revisions < routing.MAX_REVISIONS:
        upd |= {"pending_feedback": report.revision_feedback, "revision_count": revisions + 1}
        msg = f"{len(report.revision_feedback)} issue(s) → automatic revision {revisions + 1}/{routing.MAX_REVISIONS}"
    else:
        upd["quality"]["needs_human"] = True  # surfaced to a human, never silently passed
        msg = f"{len(report.revision_feedback)} issue(s) remain → needs human review"
    upd["progress"] = _progress("quality_check", msg)
    return upd


def finalize_draft(state):
    """Phase 8 terminal node. Phase 10 replaces it with the human_review interrupt."""
    needs = (state.get("quality") or {}).get("needs_human")
    return {"status": "draft_ready",
            "progress": _progress("finalize_draft", "Draft ready" + (" — flagged for human attention" if needs else ""))}
