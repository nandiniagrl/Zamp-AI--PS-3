"""Phase 5: rank verified evidence (1 Groq call, no Tavily credits).

  python -m scripts.run_rank --evidence out/evidence.json --json out/ranked.json
"""
import argparse
import json
from pathlib import Path

from app.models import Evidence, ProspectInput
from app.ranking.ranker import rank_signals


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default="out/evidence.json")
    ap.add_argument("--json", help="save ranking here")
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()

    data = json.loads(Path(args.evidence).read_text())
    prospect = ProspectInput.model_validate(data["prospect"])
    evidence = [Evidence.model_validate(e) for e in data["evidence"]]
    print(f"Seller: {prospect.seller.product} — ranking {sum(e.verification_status == 'verified' for e in evidence)} "
          f"verified signals for {prospect.name}\n")
    res = rank_signals(prospect, evidence, top_k=args.top)

    print(f"{'#':>2} {'total':>5}  {'Rel':>3} {'Spec':>4} {'Cred':>4} {'Rec':>3} {'Use':>3}  hook?  claim")
    for i, r in enumerate(res.ranked, 1):
        s = r.scores
        hook = "yes" if r.eligible_for_hook else "NO "
        print(f"{i:>2} {r.total:>5}  {s.business_relevance:>3.0f} {s.specificity:>4.0f} {s.credibility:>4.0f} "
              f"{s.recency:>3.0f} {s.outreach_usefulness:>3.0f}  {hook}   {r.claim[:90]}")
        print(f"{'':>9}why: {r.explanation}")
        if r.ineligible_reason:
            print(f"{'':>9}not usable as hook: {r.ineligible_reason}")
        print(f"{'':>9}{r.source_url}")
    print(f"\n{res.top_explanation}\n\nUsage: {res.usage}")

    if args.json:
        Path(args.json).write_text(json.dumps({**data, "ranked": [r.model_dump(mode="json") for r in res.ranked],
                                               "top_explanation": res.top_explanation}, indent=2))
        print(f"Saved ranking to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
