"""Standalone bounded draft → check → revise loop (Phase 8 reproduces this with graph edges)."""
from dataclasses import dataclass, field

from app.drafting.generator import generate_draft
from app.models import Draft, Evidence, ProspectInput, QualityReport
from app.quality.checker import check_draft

MAX_REVISIONS = 2  # → at most 3 generations in total


@dataclass
class LoopResult:
    draft: Draft
    report: QualityReport
    attempts: int
    history: list[QualityReport] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


def draft_until_pass(p: ProspectInput, hook: Evidence, supporting: list[Evidence],
                     tone: str = "professional") -> LoopResult:
    allowed = {e.id: e for e in [hook, *supporting[:1]]}
    feedback: list[str] | None = None
    history: list[QualityReport] = []
    usage: dict = {}
    for attempt in range(1, MAX_REVISIONS + 2):
        draft, u1 = generate_draft(p, hook, supporting, tone=tone, version=attempt, feedback=feedback)
        report, u2 = check_draft(draft, p, allowed)
        for u in (u1, u2):
            for k, v in u.items():
                usage[k] = usage.get(k, 0) + v
        history.append(report)
        if report.passed or report.needs_human:
            break
        feedback = report.revision_feedback
    if not report.passed:
        report = report.model_copy(update={"needs_human": True})  # surfaced to a human, never silently passed
    return LoopResult(draft=draft, report=report, attempts=len(history), history=history, usage=usage)
