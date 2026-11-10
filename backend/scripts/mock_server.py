"""DEV-ONLY MOCK server for UI work: the real FastAPI app + real LangGraph workflow, with Tavily and Groq
replaced by the labelled MOCK fixtures in tests/fixtures (fictional companies, zero API cost).

  python -m scripts.mock_server --fixture happy_path --port 8001
  (then run the frontend with BACKEND_URL=http://localhost:8001)

Never present these results as real research.
"""
import argparse
import os
from pathlib import Path

import uvicorn


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", default="happy_path")
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--delay", type=float, default=0.0, help="seconds to wait before each fake API call (to see live progress)")
    ap.add_argument("--persist", action="store_true", help="keep MOCK history + checkpoints in backend/.data/mock (SQLite)")
    args = ap.parse_args()

    if args.persist:  # separate folder so MOCK runs never mix with real history
        os.environ["CHECKPOINT_BACKEND"] = os.environ["STORAGE_BACKEND"] = "sqlite"
        os.environ["DATA_DIR"] = str(Path(__file__).resolve().parents[1] / ".data" / "mock")
    else:
        os.environ["CHECKPOINT_BACKEND"] = os.environ["STORAGE_BACKEND"] = "memory"  # nothing persisted

    from app.config import get_settings
    from app.llm import groq_client
    from app.tools import tavily_client
    from tests.fakes import FakeLLM, FakeSearch, load_fixture

    get_settings.cache_clear()
    fx = load_fixture(args.fixture)
    llm, search = FakeLLM(fx), FakeSearch(fx)
    if args.delay:
        import time

        def slow(fn):
            def wrapped(*a, **k):
                time.sleep(args.delay)
                return fn(*a, **k)
            return wrapped

        llm, search = slow(llm), slow(search)
    tavily_client.search = search
    groq_client.chat_json = groq_client.chat_json_patient = llm

    from app.api.main import app  # imported after the fakes are installed

    print(f"⚠  MOCK server on :{args.port} using tests/fixtures/{args.fixture}.json — not real research. "
          f"Prospect to enter: {fx['prospect']['name']} / {fx['prospect']['company']} / {fx['prospect']['title']}")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
