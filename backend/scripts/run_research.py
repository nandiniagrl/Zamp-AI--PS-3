"""Phase 3: run person/company/hiring research for one prospect (≈5 free Tavily credits; cached 24h).

  python -m scripts.run_research --input samples/prospect_example.json --json out/research.json
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from app.models import ProspectInput
from app.research.pipeline import research_all


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="prospect JSON file")
    ap.add_argument("--json", help="save research records here (reused by later phases, saves credits)")
    args = ap.parse_args()

    prospect = ProspectInput.model_validate_json(Path(args.input).read_text())
    print(f"Researching {prospect.name} — {prospect.title} at {prospect.company}\n")
    res = research_all(prospect)

    print("Records per branch:", dict(Counter(r.branch for r in res.records)))
    for i, r in enumerate(res.records, 1):
        flag = "  ⚠ injection-like text removed" if r.injection_flagged else ""
        print(f"{i:2d}. [{r.branch:7s}] {r.published_date or 'no date':32s} {r.domain}{flag}")
        print(f"    {r.title[:100]}")
        print(f"    {r.url}")
    if res.errors:
        print("\nErrors (other branches still returned):")
        for e in res.errors:
            print("  -", e)
    print("\nUsage:", res.usage)

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"prospect": prospect.model_dump(mode="json"),
                                   "records": [r.model_dump(mode="json") for r in res.records],
                                   "errors": res.errors, "usage": res.usage}, indent=2))
        print(f"Saved {len(res.records)} records to {out}")
    return 0 if res.records else 1


if __name__ == "__main__":
    raise SystemExit(main())
