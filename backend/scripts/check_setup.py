"""Phase 0 sanity check: Python version, dependency imports, credential presence (never values).

Run from backend/:  python -m scripts.check_setup
"""
import importlib
import importlib.metadata as md
import sys

REQUIRED = {
    "dotenv": "python-dotenv",
    "pydantic": "pydantic",
    "pydantic_settings": "pydantic-settings",
    "groq": "groq",
    "tavily": "tavily-python",
    "langgraph": "langgraph",
    "tenacity": "tenacity",
    "rapidfuzz": "rapidfuzz",
}


def main() -> int:
    ok = True
    print(f"Python {sys.version.split()[0]}")
    if sys.version_info < (3, 11):
        print("  ✗ Python 3.11+ required")
        ok = False
    for module, dist in REQUIRED.items():
        try:
            importlib.import_module(module)
            print(f"  ✓ {dist} {md.version(dist)}")
        except Exception as exc:  # report every failure, don't stop at the first
            print(f"  ✗ {dist}: {exc}")
            ok = False

    from app.config import get_settings

    settings = get_settings()
    print(f"Environment: {settings.app_env}")
    for name, state in settings.key_status().items():
        print(f"  {name}: {state}")
    print("RESULT:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
