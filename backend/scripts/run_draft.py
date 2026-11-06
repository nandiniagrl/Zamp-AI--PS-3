"""Phase 6: write one email from saved ranking (1 Groq call, no Tavily credits).

  python -m scripts.run_draft --ranked out/ranked.json [--tone friendly] [--hook ev_xxx] [--json out/draft.json]
"""
import argparse
import json
from pathlib import Path

from app.drafting.generator import generate_draft
from app.models import Evidence, ProspectInput, RankedSignal


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ranked", default="out/ranked.json")
    ap.add_argument("--tone", choices=["professional", "friendly", "direct"])
    ap.add_argument("--hook", help="evidence_id to use instead of the top-ranked signal")
    ap.add_argument("--instructions")
    ap.add_argument("--json")
    args = ap.parse_args()

    data = json.loads(Path(args.ranked).read_text())
    p = ProspectInput.model_validate(data["prospect"])
    evidence = {e["id"]: Evidence.model_validate(e) for e in data["evidence"]}
    eligible = [RankedSignal.model_validate(r) for r in data["ranked"] if r["eligible_for_hook"]]
    if not eligible:
        print("Insufficient verified research: no eligible hook. Nothing drafted.")
        return 1
    hook_id = args.hook or eligible[0].evidence_id
    if hook_id not in {r.evidence_id for r in eligible}:
        print(f"{hook_id} is not an eligible signal. Choose from: {[r.evidence_id for r in eligible]}")
        return 1
    supporting = [evidence[r.evidence_id] for r in eligible if r.evidence_id != hook_id][:1]

    draft, usage = generate_draft(p, evidence[hook_id], supporting, tone=args.tone or p.tone,
                                  instructions=args.instructions)
    print(f"Subject: {draft.subject}\n\n{draft.body}\n")
    print(f"— {draft.word_count} words, tone={draft.tone}")
    print(f"— Hook: {evidence[hook_id].claim}\n  {evidence[hook_id].source_url}")
    print("— Claims used:")
    for c in draft.claims_used:
        src = evidence[c.evidence_id].source_url if c.evidence_id in evidence else "⚠ UNKNOWN evidence id"
        print(f"   • {c.text}  [{c.evidence_id}] {src}")
    print(f"Usage: {usage}")
    if args.json:
        Path(args.json).write_text(json.dumps({**data, "draft": draft.model_dump(mode="json")}, indent=2))
        print(f"Saved draft to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
