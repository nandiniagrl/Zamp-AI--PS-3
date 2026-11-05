"""Tiny JSON-file cache with a TTL, used to avoid re-spending free Tavily credits during development.

Keys are hashes of request parameters only; API keys are never part of the params, so nothing secret is stored.
"""
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from app.config import get_settings


def make_key(namespace: str, params: dict) -> str:
    blob = json.dumps(params, sort_keys=True, default=str)
    return f"{namespace}-{hashlib.sha256(blob.encode()).hexdigest()[:32]}"


def _path(key: str) -> Path:
    d = get_settings().cache_dir
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.json"


def get(key: str) -> Any | None:
    s = get_settings()
    if not s.cache_enabled:
        return None
    p = _path(key)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if time.time() - data.get("ts", 0) > s.cache_ttl_hours * 3600:
        return None
    return data.get("value")


def set(key: str, value: Any) -> None:  # noqa: A001 - mirrors dict-style API
    if not get_settings().cache_enabled:
        return
    p = _path(key)
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump({"ts": time.time(), "value": value}, f)
    os.replace(tmp, p)  # atomic: safe when parallel research branches write at once
