"""Integrity-focused JSON helpers for local learning-memory files.

Memory is user data.  A malformed or partially-written file must therefore be
reported instead of silently treated as an empty store, because the latter can
turn the next save into irreversible data loss.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any


class MemoryStoreError(RuntimeError):
    """Raised when persisted learning memory cannot be read or written safely."""


MAX_MEMORY_FILE_BYTES = 16 * 1024 * 1024


def read_json(path: Path, default: Any = None):
    """Read JSON from *path* without hiding corruption.

    A missing file is a normal first-run condition and returns ``default``.
    Invalid JSON and I/O errors raise :class:`MemoryStoreError`, preventing a
    caller from mistaking damaged user data for an empty memory store.
    """

    path = Path(path)
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise MemoryStoreError(f"Memory path is not a regular file: {path}")
        if file_stat.st_size > MAX_MEMORY_FILE_BYTES:
            raise MemoryStoreError(
                f"Memory file exceeds {MAX_MEMORY_FILE_BYTES} bytes: {path}"
            )
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            raw = stream.read(MAX_MEMORY_FILE_BYTES + 1)
        if len(raw) > MAX_MEMORY_FILE_BYTES:
            raise MemoryStoreError(
                f"Memory file exceeds {MAX_MEMORY_FILE_BYTES} bytes: {path}"
            )
        return json.loads(raw.decode("utf-8"))
    except FileNotFoundError:
        return default
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        line = getattr(exc, "lineno", "?")
        column = getattr(exc, "colno", "?")
        raise MemoryStoreError(
            f"Memory file is not valid JSON or UTF-8: {path} (line {line}, column {column})"
        ) from exc
    except MemoryStoreError:
        raise
    except OSError as exc:
        raise MemoryStoreError(f"Unable to read memory file: {path}: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def write_json(path: Path, data: Any, *, keep_backup: bool = True) -> None:
    """Atomically persist JSON and optionally retain the previous version.

    The new content is flushed and fsynced in the destination directory before
    ``os.replace`` swaps it into place.  Readers therefore see either the old
    complete document or the new complete document, never a partial write.
    """

    path = Path(path)
    temp_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as f:
            temp_path = Path(f.name)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())

        if keep_backup and path.exists():
            backup_path = path.with_name(f"{path.name}.bak")
            shutil.copy2(path, backup_path)

        os.replace(temp_path, path)
        temp_path = None
    except (OSError, TypeError, ValueError) as exc:
        raise MemoryStoreError(f"Unable to write memory file safely: {path}: {exc}") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def iter_memory_items(data) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("words"), list):
            return [item for item in data["words"] if isinstance(item, dict)]
        return [item for item in data.values() if isinstance(item, dict)]
    return []
