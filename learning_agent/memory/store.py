"""Small JSON store helpers for memory data files."""

from __future__ import annotations

import json
from pathlib import Path


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def iter_memory_items(data) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("words"), list):
            return [item for item in data["words"] if isinstance(item, dict)]
        return [item for item in data.values() if isinstance(item, dict)]
    return []
