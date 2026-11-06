"""Write the workflow diagram to docs/graph.mmd (open in VS Code with a Mermaid preview, or mermaid.live).

  python -m scripts.draw_graph
"""
from pathlib import Path

from app.graph.builder import build_graph

OUT = Path(__file__).resolve().parents[2] / "docs" / "graph.mmd"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_graph().get_graph().draw_mermaid())
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
