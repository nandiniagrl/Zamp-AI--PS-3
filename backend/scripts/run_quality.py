"""Phase 7 quality checks.

  python -m scripts.run_quality --draft out/draft.json     # check the Phase 6 draft (1 Groq call)
  python -m scripts.run_quality --flawed                    # check a deliberately flawed draft
  python -m scripts.run_quality --loop                      # live draft → check → revise loop (≤3 drafts)
"""
import argparse
import json
from pathlib import Path

from app.models import ClaimRef, Draft, Evidence, ProspectInput, QualityReport, RankedSignal
from app.quality.checker import check_draft
from app.quality.loop import draft_until_pass
from app.utils.text import word_count

ICON = {"fail": "❌", "warn": "⚠️ "}


def show(report: QualityReport, title: str) -> None:
    status = "PASSED" if report.passed else ("NEEDS HUMAN REVIEW" if report.needs_human else "FAILED")
    print(f"\n== {title}: {status}")
    for i in report.issues:
        print(f"   {ICON[i.severity]} [{i.check}] {i.message}")
    if not report.issues:
        print("   ✅ no issues")


def flawed_draft(hook_id: str) -> Draft:
    body = ("Hi Patrick,\n\nI hope this email finds you well! I've been a big fan of Stripe for years and your "
            "visionary leadership is truly amazing. " + "We help companies like yours do more with less. " * 8 +
            "LedgerLens customers cut reconciliation costs by 40% in the first month, guaranteed. "
            "Let me know when [Company] can hop on a quick call.\n\nBest,\n[Your name]")
    return Draft(subject="Quick question!!!", body=body, hook_evidence_id=hook_id,
                 claims_used=[ClaimRef(text="Stripe won an award", evidence_id="ev_does_not_exist")],
                 word_count=word_count(body))


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--draft", help="draft JSON from run_draft --json")
    g.add_argument("--flawed", action="store_true")
    g.add_argument("--loop", action="store_true")
    ap.add_argument("--ranked", default="out/ranked.json")
    args = ap.parse_args()

    data = json.loads(Path(args.draft or args.ranked).read_text())
    p = ProspectInput.model_validate(data["prospect"])
    ev = {e["id"]: Evidence.model_validate(e) for e in data["evidence"]}
    eligible = [RankedSignal.model_validate(r) for r in data["ranked"] if r["eligible_for_hook"]]
    hook = ev[eligible[0].evidence_id]
    supporting = [ev[r.evidence_id] for r in eligible[1:2]]
    allowed = {e.id: e for e in [hook, *supporting]}

    if args.flawed or args.draft:
        d = flawed_draft(hook.id) if args.flawed else Draft.model_validate(data["draft"])
        if args.draft:
            allowed = {i: ev[i] for i in [d.hook_evidence_id, *d.supporting_evidence_ids] if i in ev}
        print(f"Subject: {d.subject}\n\n{d.body}")
        report, usage = check_draft(d, p, allowed)
        show(report, "Quality check")
        print("\nUsage:", usage)
        return 0

    res = draft_until_pass(p, hook, supporting, tone=p.tone)
    for n, rep in enumerate(res.history, 1):
        show(rep, f"Attempt {n}")
    print(f"\nFinal draft (v{res.draft.version}, {res.draft.word_count} words) after {res.attempts} attempt(s):\n")
    print(f"Subject: {res.draft.subject}\n\n{res.draft.body}")
    show(res.report, "Final status")
    print("\nUsage:", res.usage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
