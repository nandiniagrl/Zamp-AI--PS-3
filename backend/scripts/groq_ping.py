"""Phase 1 connectivity check.

  python -m scripts.groq_ping                # real text + structured (JSON) request
  python -m scripts.groq_ping --list-models  # confirm configured model names exist
"""
import argparse

import groq
from pydantic import BaseModel

from app.config import get_settings
from app.llm import groq_client as llm


class Ping(BaseModel):
    answer: str
    confidence: str


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-models", action="store_true")
    args = ap.parse_args()
    s = get_settings()
    try:
        if args.list_models:
            ids = sorted(m.id for m in llm.get_client().models.list().data)
            print("\n".join(ids))
            for label, name in (("GROQ_MODEL", s.groq_model), ("GROQ_FAST_MODEL", s.groq_fast_model)):
                print(f"{label}={name}: {'OK' if name in ids else 'NOT FOUND'}")
            return 0
        text, u1 = llm.chat_text("In one sentence, what is B2B sales outreach?")
        obj, u2 = llm.chat_json(Ping, system="Answer briefly.", user="Is Python a programming language? Reply in JSON.")
        print(f"Model: {s.groq_model}")
        print(f"Text response: {text}")
        print(f"Structured response: {obj.model_dump()}")
        print(f"Usage: text={u1.as_dict()} json={u2.as_dict()}")
        return 0
    except llm.LLMError as e:
        print(f"ERROR: {e}")
        return 1
    except groq.APIError as e:  # e.g. models.list() failures
        print(f"ERROR: Groq API error ({type(e).__name__}).")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
