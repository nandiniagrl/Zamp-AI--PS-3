"""Terminal human-review demo with durable checkpoints (backend/.data/checkpoints.sqlite).

  python -m scripts.review_cli start --input samples/prospect_example.json     # LIVE: runs until it pauses, then exits
  python -m scripts.review_cli start --fixture happy_path                      # MOCK
  python -m scripts.review_cli show   <run_id> [--fixture happy_path]
  python -m scripts.review_cli resume <run_id> [--fixture happy_path] [--answer '{"action": "approve"}']
      (without --answer you are prompted interactively)

The run survives closing the terminal: `resume` builds a new graph with a new DB connection and continues
the same thread_id. This tool never sends email.
"""
import argparse
import json
import uuid
from pathlib import Path

from langgraph.types import Command

from app.config import get_settings
from app.graph.builder import build_graph
from app.graph.checkpoint import make_checkpointer
from app.graph.state import initial_state
from app.models import ProspectInput


def _graph():
    s = get_settings().model_copy(update={"checkpoint_backend": "sqlite"})
    return build_graph(make_checkpointer(s))


def _config(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}, "recursion_limit": 60}


def _stream(graph, payload, config) -> None:
    for chunk in graph.stream(payload, config, stream_mode="updates"):
        for node, update in chunk.items():
            for p in (update or {}).get("progress", []) if node != "__interrupt__" else []:
                print(f"  ▶ {node:20s} {p['message']}")


def _show(graph, run_id: str) -> dict | None:
    snap = graph.get_state(_config(run_id))
    if not snap.values:
        print(f"No run found with id {run_id}")
        return None
    v = snap.values
    pending = snap.interrupts[0].value if snap.interrupts else None
    print(f"\nRun {run_id} — {v['prospect']['name']} at {v['prospect']['company']} — status: "
          f"{'paused (' + pending['type'] + ')' if pending else v.get('status')}")
    draft = (pending or {}).get("draft") or v.get("final_draft") or v.get("draft")
    if draft:
        print(f"\n  Subject: {draft['subject']}\n\n" + "\n".join("  " + line for line in draft["body"].splitlines()))
        q = (pending or {}).get("quality") or v.get("quality") or {}
        print(f"\n  Quality: {'PASSED' if q.get('passed') else 'NEEDS ATTENTION'}"
              + "".join(f"\n    - [{i['check']}] {i['message']}" for i in q.get("issues", [])))
    if pending and pending["type"] == "review":
        print("\n  Alternative verified signals:")
        for a in pending["alternatives"]:
            print(f"    {a['evidence_id']}  ({a['total']}/100) {a['claim'][:90]}")
        print(f"\n  {pending['note']}")
    if pending:
        print(f"\n  Options: {json.dumps(pending.get('options', {}))}")
    return pending


def _ask(pending: dict) -> dict:
    if pending["type"] != "review":
        return json.loads(input("Answer as JSON: "))
    action = input("\nAction [approve/edit/reject/choose_signal/regenerate]: ").strip()
    if action == "edit":
        print("Paste the new body; finish with a line containing only END")
        lines = []
        while (line := input()) != "END":
            lines.append(line)
        return {"action": "edit", "body": "\n".join(lines)}
    if action == "choose_signal":
        return {"action": action, "evidence_id": input("evidence_id: ").strip()}
    if action == "regenerate":
        return {"action": action, "instructions": input("Instructions (optional): ").strip() or None}
    if action == "reject":
        return {"action": action, "reason": input("Reason (optional): ").strip() or None}
    return {"action": "approve"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["start", "show", "resume"])
    ap.add_argument("run_id", nargs="?")
    ap.add_argument("--input")
    ap.add_argument("--fixture", help="use MOCK fixture fakes (needed again on resume if it redrafts)")
    ap.add_argument("--answer", help="JSON answer for the pending pause")
    args = ap.parse_args()

    if args.fixture:
        from scripts.run_graph import install_mock
        fx = install_mock(args.fixture)
        print(f"⚠ MOCK mode (tests/fixtures/{args.fixture}.json) — not real research")
    graph = _graph()

    if args.command == "start":
        prospect = (ProspectInput.model_validate(fx["prospect"]) if args.fixture
                    else ProspectInput.model_validate_json(Path(args.input).read_text()))
        run_id = uuid.uuid4().hex[:12]
        print(f"Starting run {run_id}: {prospect.name} at {prospect.company}")
        _stream(graph, initial_state(run_id, prospect.model_dump(mode="json")), _config(run_id))
        _show(graph, run_id)
        print(f"\nPaused and saved. Resume later (even after closing this terminal):\n"
              f"  python -m scripts.review_cli resume {run_id}" + (f" --fixture {args.fixture}" if args.fixture else ""))
        return 0

    if not args.run_id:
        ap.error("run_id is required")
    pending = _show(graph, args.run_id)
    if args.command == "show" or pending is None:
        return 0
    answer = json.loads(args.answer) if args.answer else _ask(pending)
    print(f"\n▶ Resuming {args.run_id} with {answer}")
    _stream(graph, Command(resume=answer), _config(args.run_id))
    _show(graph, args.run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
