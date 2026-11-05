"""Phase 4: verify claims from saved research (no Tavily credits; uses Groq free-tier tokens).

  python -m scripts.run_verify --research out/research.json --json out/evidence.json
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from app.models import ProspectInput, ResearchRecord
from app.verification.verifier import verify

ICON = {"verified": "✅", "uncertain": "❔", "disputed": "⚠️", "rejected": "❌"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--research", default="out/research.json")
    ap.add_argument("--json", help="save evidence here")
    args = ap.parse_args()

    data = json.loads(Path(args.research).read_text())
    prospect = ProspectInput.model_validate(data["prospect"])
    records = [ResearchRecord.model_validate(r) for r in data["records"]]
    print(f"Verifying claims from {len(records)} sources for {prospect.name} ({prospect.company})…\n")
    res = verify(prospect, records)

    order = {"verified": 0, "uncertain": 1, "disputed": 2, "rejected": 3}
    for i, e in enumerate(sorted(res.evidence, key=lambda x: order[x.verification_status]), 1):
        sens = f"  🔶 sensitive: {e.sensitive_category}" if e.is_sensitive else ""
        print(f"{i:2d}. {ICON[e.verification_status]} {e.verification_status:9s} cred={e.credibility:6s} "
              f"assoc={e.association:9s} [{e.claim_type}]{sens}")
        print(f"    claim : {e.claim}")
        print(f'    quote : "{e.quote[:160]}"')
        print(f"    source: {e.source_url}  ({e.credibility_reason}; date={e.publication_date or 'n/a'})")
        if e.corroborating_urls:
            print(f"    also  : {', '.join(e.corroborating_urls)}")
        for n in e.notes:
            print(f"    note  : {n}")
    print("\nSummary:", dict(Counter(e.verification_status for e in res.evidence)))
    for c in res.conflicts:
        print(f"Conflict [{c.status}] {c.claim_type}/{c.key}: {' vs '.join(c.values)} — {c.note}")
    for err in res.errors:
        print("Error:", err)
    print("Usage:", res.usage)

    if args.json:
        Path(args.json).write_text(json.dumps({
            "prospect": prospect.model_dump(mode="json"),
            "evidence": [e.model_dump(mode="json") for e in res.evidence],
            "conflicts": [c.model_dump(mode="json") for c in res.conflicts],
            "usage": res.usage, "errors": res.errors}, indent=2))
        print(f"Saved {len(res.evidence)} evidence objects to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
