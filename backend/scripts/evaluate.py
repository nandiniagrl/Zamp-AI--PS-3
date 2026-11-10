"""Phase 15 — end-to-end evaluation: run real prospects through the full workflow (up to the first pause)
and measure time, cost, quality and whether every claim in the email is backed by its source.

  python -m scripts.evaluate --prospects samples/eval_set.json            # LIVE (Tavily credits + Groq tokens)
  python -m scripts.evaluate --fixture happy_path --fixture sensitive_news # MOCK fixtures, no API calls

Writes out/eval_report.json. Nothing is ever sent: the run stops at the human-review pause.
"""
import argparse
import json
import time
import uuid
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from app.graph.builder import build_graph
from app.graph.state import initial_state
from app.models import ProspectInput
from app.verification.verifier import quote_supported

OUT = Path(__file__).resolve().parents[1] / "out" / "eval_report.json"


def audit_claims(state: dict) -> dict:
    """Every claim in the draft must cite VERIFIED, non-sensitive evidence whose quote is in the retrieved text."""
    draft = state.get("draft") or {}
    evidence = {e["id"]: e for e in state.get("evidence", [])}
    sources = {}
    for r in state.get("research", []):
        sources.setdefault(r["url"], f"{r['title']} {r['content']}")
    rows = []
    for c in draft.get("claims_used", []):
        e = evidence.get(c["evidence_id"])
        problems = []
        if e is None:
            problems.append("cites unknown evidence")
        else:
            if e["verification_status"] != "verified":
                problems.append(f"evidence is {e['verification_status']}")
            if e["is_sensitive"]:
                problems.append("evidence is sensitive")
            if not quote_supported(e["quote"], sources.get(e["source_url"], "")):
                problems.append("quote not found in retrieved source text")
        rows.append({"claim": c["text"], "evidence_id": c["evidence_id"],
                     "source_url": e and e["source_url"], "ok": not problems, "problems": problems})
    supported = sum(r["ok"] for r in rows)
    return {"claims": len(rows), "supported": supported,
            "rate": round(supported / len(rows), 3) if rows else None, "rows": rows}


def run_one(prospect: ProspectInput, label: str) -> dict:
    graph, run_id = build_graph(InMemorySaver()), uuid.uuid4().hex[:12]
    config = {"configurable": {"thread_id": run_id}, "recursion_limit": 60}
    node_seconds: dict[str, float] = {}
    t0 = last = time.perf_counter()
    for chunk in graph.stream(initial_state(run_id, prospect.model_dump(mode="json")), config, stream_mode="updates"):
        now = time.perf_counter()
        for node in chunk:
            if node != "__interrupt__":  # parallel branches finishing together share the step's time
                node_seconds[node] = round(node_seconds.get(node, 0) + (now - last) / len(chunk), 2)
        last = now
    total = round(time.perf_counter() - t0, 1)
    snap = graph.get_state(config)
    s = snap.values
    pending = snap.interrupts[0].value["type"] if snap.interrupts else None
    usage = s.get("usage", {})
    quality = s.get("quality") or {}
    return {
        "label": label, "prospect": f"{prospect.name} — {prospect.title} at {prospect.company}",
        "paused_at": pending, "status": s.get("status"), "seconds": total, "node_seconds": node_seconds,
        "tavily_credits": usage.get("tavily_credits", 0), "tavily_cache_hits": usage.get("cache_hits", 0),
        "groq_calls": usage.get("groq_calls", 0),
        "groq_tokens": usage.get("groq_prompt_tokens", 0) + usage.get("groq_completion_tokens", 0),
        "evidence": {k: sum(e["verification_status"] == k for e in s.get("evidence", []))
                     for k in ("verified", "uncertain", "disputed", "rejected")},
        "edge_cases": sorted({e["case"] for e in s.get("edge_cases", [])}),
        "edge_case_notes": [f"{e['case']}: {e['message']} → {e['action']}" for e in s.get("edge_cases", [])],
        "draft": bool(s.get("draft")),
        "quality_first_try": bool(s.get("draft")) and s.get("revision_count", 0) == 0 and bool(quality.get("passed")),
        "quality_passed": bool(quality.get("passed")), "revisions": s.get("revision_count", 0),
        "word_count": (s.get("draft") or {}).get("word_count"),
        "subject": (s.get("draft") or {}).get("subject"),
        "claim_audit": audit_claims(s),
        "errors": s.get("research_errors", []),
    }


def summarise(results: list[dict]) -> dict:
    drafted = [r for r in results if r["draft"]]
    claims = sum(r["claim_audit"]["claims"] for r in results)
    ok = sum(r["claim_audit"]["supported"] for r in results)
    n = len(results) or 1
    return {"runs": len(results), "drafted": len(drafted),
            "avg_seconds": round(sum(r["seconds"] for r in results) / n, 1),
            "max_seconds": max((r["seconds"] for r in results), default=0),
            "avg_tavily_credits": round(sum(r["tavily_credits"] for r in results) / n, 1),
            "avg_groq_tokens": round(sum(r["groq_tokens"] for r in results) / n),
            "claim_audit": f"{ok}/{claims}", "claim_audit_rate": round(ok / claims, 3) if claims else None,
            "quality_first_try": f"{sum(r['quality_first_try'] for r in drafted)}/{len(drafted)}",
            "edge_cases_seen": sorted({c for r in results for c in r["edge_cases"]}),
            "sent_emails": 0}


def print_table(results: list[dict], summary: dict) -> None:
    print(f"\n{'prospect':44s} {'pause':12s} {'sec':>6s} {'credits':>7s} {'tokens':>7s} {'claims ok':>9s} {'QC 1st':>6s} edge")
    for r in results:
        a = r["claim_audit"]
        print(f"{r['prospect'][:44]:44s} {str(r['paused_at'] or r['status']):12s} {r['seconds']:6.1f} "
              f"{r['tavily_credits']:7d} {r['groq_tokens']:7d} {str(a['supported']) + '/' + str(a['claims']):>9s} "
              f"{'yes' if r['quality_first_try'] else '-':>6s} {','.join(r['edge_cases']) or '-'}")
        for row in a["rows"]:
            if not row["ok"]:
                print(f"   ✗ {row['claim'][:70]} — {', '.join(row['problems'])}")
    print("\nSUMMARY", json.dumps(summary, indent=1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prospects", help="JSON list of prospects (LIVE)")
    ap.add_argument("--fixture", action="append", default=[], help="MOCK fixture name(s); no API calls")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    results = []
    if args.prospects:
        for p in json.loads(Path(args.prospects).read_text()):
            prospect = ProspectInput.model_validate(p)
            print(f"▶ {prospect.name} at {prospect.company} …", flush=True)
            results.append(run_one(prospect, "live"))
    for name in args.fixture:
        from scripts.run_graph import install_mock

        prospect = ProspectInput.model_validate(install_mock(name)["prospect"])
        results.append(run_one(prospect, f"MOCK:{name}"))
    if not results:
        ap.error("give --prospects and/or --fixture")
    summary = summarise(results)
    print_table(results, summary)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"summary": summary, "runs": results}, indent=1))
    print(f"\nSaved {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
