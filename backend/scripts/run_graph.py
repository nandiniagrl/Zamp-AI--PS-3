"""Run the full LangGraph workflow and stream node-by-node progress.

  python -m scripts.run_graph --input samples/prospect_example.json   # LIVE (≈5 Tavily credits + Groq)
  python -m scripts.run_graph --fixture happy_path                    # MOCK data, no API calls
  python -m scripts.run_graph --fixture identity_ambiguous --resume '{"candidate_id": "c2"}'
      --resume answers a pause (interrupt) with JSON; repeat it to answer several pauses in order.
"""
import argparse
import json
import time
import uuid
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph.builder import build_graph
from app.graph.state import initial_state
from app.models import ProspectInput


def install_mock(fixture: str) -> dict:
    """Swap Tavily/Groq for the labelled MOCK fixture (same fakes as the unit tests)."""
    from app.llm import groq_client
    from app.tools import tavily_client
    from tests.fakes import FakeLLM, FakeSearch, load_fixture

    fx = load_fixture(fixture)
    llm = FakeLLM(fx)
    tavily_client.search = FakeSearch(fx)
    groq_client.chat_json = groq_client.chat_json_patient = llm
    return fx


def main() -> int:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="prospect JSON (live run)")
    src.add_argument("--fixture", help="MOCK fixture name in tests/fixtures (no API calls)")
    ap.add_argument("--json", help="save final state here")
    ap.add_argument("--resume", action="append", default=[], help="JSON answer for the next pause")
    args = ap.parse_args()

    if args.fixture:
        prospect = ProspectInput.model_validate(install_mock(args.fixture)["prospect"])
        print(f"⚠ MOCK RUN using tests/fixtures/{args.fixture}.json — not real research\n")
    else:
        prospect = ProspectInput.model_validate_json(Path(args.input).read_text())

    graph, run_id = build_graph(InMemorySaver()), uuid.uuid4().hex[:12]
    config = {"configurable": {"thread_id": run_id}, "recursion_limit": 60}
    print(f"Run {run_id}: {prospect.name} — {prospect.title} at {prospect.company}\n")
    start = time.time()
    payload = initial_state(run_id, prospect.model_dump(mode="json"))
    answers = list(args.resume)
    while True:
        for chunk in graph.stream(payload, config, stream_mode="updates"):
            for node, update in chunk.items():
                if node == "__interrupt__":
                    continue
                for p in (update or {}).get("progress", []):
                    print(f"[{time.time() - start:5.1f}s] ▶ {node:18s} {p['message']}")
        snap = graph.get_state(config)
        if not snap.interrupts:
            break
        pending = snap.interrupts[0].value
        print(f"\n⏸  PAUSED ({pending['type']}): {pending.get('message', '')}")
        for c in pending.get("candidates", []):
            print(f"     {c['id']}: {c['name']} — {c.get('title')} at {c.get('company')}  ({c['source_url']})")
        for cf in pending.get("conflicts", []):
            print(f"     conflict {cf['id']} ({cf['key']}):")
            for e in cf["evidence"]:
                print(f"        {e['id']}: \"{e['value']}\" — {e['source_domain']} ({e.get('publication_date') or 'no date'})")
        if pending.get("options"):
            print(f"     options: {json.dumps(pending['options'])}")
        if not answers:
            print("\n(Re-run with --resume '<json>' to answer this pause.)")
            break
        answer = json.loads(answers.pop(0))
        print(f"▶ resuming with {answer}\n")
        payload = Command(resume=answer)

    snap = graph.get_state(config)
    state = snap.values
    status = f"paused — waiting for your '{snap.interrupts[0].value['type']}' answer" if snap.interrupts else state.get("status")
    print(f"\nSTATUS: {status}")
    if state.get("top_explanation"):
        print(f"\nWHY THIS HOOK: {state['top_explanation']}")
    if d := state.get("draft"):
        q = state.get("quality") or {}
        print(f"\nSubject: {d['subject']}\n\n{d['body']}\n")
        print(f"Quality: {'PASSED' if q.get('passed') else 'NEEDS HUMAN REVIEW'}")
        for i in q.get("issues", []):
            print(f"   {'❌' if i['severity'] == 'fail' else '⚠️ '} [{i['check']}] {i['message']}")
        ev = {e["id"]: e for e in state["evidence"]}
        for c in d["claims_used"]:
            print(f"   source for '{c['text'][:60]}': {ev.get(c['evidence_id'], {}).get('source_url', '⚠ unknown')}")
    for e in state.get("research_errors", []):
        print("Error:", e)
    print(f"\nUSAGE: {json.dumps(state.get('usage', {}))}  |  total {time.time() - start:.1f}s")
    if args.json:
        Path(args.json).write_text(json.dumps(state, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
