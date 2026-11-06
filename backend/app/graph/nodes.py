"""Graph nodes: thin adapters that re-validate state, call one module, and return JSON updates.
Each node appends a human-readable `progress` entry so every step is inspectable."""
from datetime import datetime, timezone

from app.drafting.generator import generate_draft
from app.graph import routing
from app.models import Draft, Evidence, ProspectInput, RankedSignal, ResearchRecord
from app.quality.checker import check_draft
from app.ranking.ranker import rank_signals as rank
from app.research import pipeline
from app.verification import verifier


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _p(state) -> ProspectInput:
    return ProspectInput.model_validate(state["prospect"])


def _progress(node: str, message: str) -> list[dict]:
    return [{"node": node, "message": message, "ts": _now()}]


def _dump(items) -> list[dict]:
    return [i.model_dump(mode="json") for i in items]


# ---------------------------------------------------------------- identity
def resolve_prospect(state):
    """Phase 8 placeholder: identity is accepted as entered. Phase 9A adds real identity resolution."""
    p = _p(state)
    identity = {"status": "confirmed", "candidates": [], "selected_id": None,
                "explanation": f"Using {p.name}, {p.title} at {p.company} as entered (identity checks added in Phase 9A)."}
    return {"identity": identity, "status": "researching", "progress": _progress("resolve_prospect", identity["explanation"])}


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
    if n_eligible == 0:
        upd["status"] = "insufficient"  # Phase 9B replaces this with broaden → ask-for-context
    return upd


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
