#!/usr/bin/env python3
"""Deterministic memory CLI for content-memory Skills.

Skill 对话层负责理解和出题，而复习状态（间隔、连击、到期时间）的读写一律
通过本 CLI 完成，避免由模型手写 JSON 造成的字段漂移和静默数据损坏。所有
写入都经过 :mod:`learning_agent.memory.store` 的原子写 + 备份路径。

用法（在项目根目录）::

    python -m learning_agent.memory.cli add --skill word-deep-dive --id complimentary --word complimentary --exam 六级
    python -m learning_agent.memory.cli due --skill word-deep-dive --limit 6
    python -m learning_agent.memory.cli grade --skill word-deep-dive --id complimentary --correct
    python -m learning_agent.memory.cli status --skill word-deep-dive --json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from learning_agent.memory.scheduler import (
    MemoryState,
    enrich_item,
    schedule_review,
    sort_for_review,
)
from learning_agent.memory.store import MemoryStoreError, read_json, write_json


CONTENT_SKILLS = ("word-deep-dive", "text-memorizer")

# 每个 skill 的存储文件：文件名 -> 可选的列表包装键（None 表示顶层就是列表）。
SKILL_FILES: dict[str, dict[str, str | None]] = {
    "word-deep-dive": {"words.json": "words"},
    "text-memorizer": {"questions.json": None, "weak_points.json": None},
}

TEXT_FILE_ALIASES = {"questions": "questions.json", "weak-points": "weak_points.json"}

DEFAULT_DUE_LIMIT = 6
WEAK_STREAK_THRESHOLD = 2

MAX_ID_CHARS = 200
MAX_FIELD_CHARS = 100_000


def default_memory_root() -> Path:
    return Path.cwd() / "memory"


def _is_due(item: dict, today: date) -> bool:
    """review-engine.md 的抽取条件：next_review <= 今天（含当天）。"""

    next_review = item.get("next_review")
    if next_review is None:
        return True
    due_day = _parse_day(next_review)
    if due_day is None:
        return True
    return due_day <= today


def _today(args_today: str | None) -> date:
    if args_today is None:
        return date.today()
    parsed = _parse_day(args_today)
    if parsed is None:
        raise ValueError(f"--today 必须是 YYYY-MM-DD：{args_today}")
    return parsed


def _parse_day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _require_str(value: Any, field: str, *, max_chars: int = MAX_FIELD_CHARS) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} 必须是非空字符串")
    if len(value) > max_chars:
        raise ValueError(f"{field} 超过 {max_chars} 字符")
    return value.strip()


def _validate_item(item: dict, location: str) -> None:
    if not isinstance(item, dict):
        raise MemoryStoreError(f"记忆结构无效：{location} 必须是 JSON 对象")
    try:
        MemoryState.from_item(item)
    except ValueError as exc:
        raise MemoryStoreError(f"记忆结构无效：{location}：{exc}") from exc
    _require_str(item.get("id"), f"{location} 的 id", max_chars=MAX_ID_CHARS)
    for field in ("created_at", "last_reviewed", "next_review"):
        value = item.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or _parse_day(value) is None:
            raise MemoryStoreError(f"记忆结构无效：{location} 的 {field} 必须是 YYYY-MM-DD 或 null")
    for field in ("word", "content", "exam", "module", "note", "title", "question"):
        if field in item and item[field] is not None and not isinstance(item[field], str):
            raise MemoryStoreError(f"记忆结构无效：{location} 的 {field} 必须是字符串")


def _resolve_file(skill: str, file_alias: str | None, memory_root: Path) -> tuple[Path, str | None]:
    if skill not in SKILL_FILES:
        raise ValueError(
            f"--skill 必须是 {' 或 '.join(CONTENT_SKILLS)}：{skill}"
        )
    files = SKILL_FILES[skill]
    if len(files) == 1:
        filename, wrapper = next(iter(files.items()))
        return memory_root / skill / filename, wrapper
    alias = file_alias or "questions"
    if alias not in TEXT_FILE_ALIASES:
        raise ValueError(f"text-memorizer 需要 --file questions 或 --file weak-points：{alias!r}")
    filename = TEXT_FILE_ALIASES[alias]
    return memory_root / skill / filename, files[filename]


def _load_items(path: Path, wrapper: str | None) -> tuple[list[dict], str | None]:
    data = read_json(path)
    if data is None:
        return [], wrapper
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and wrapper and isinstance(data.get(wrapper), list):
        return list(data[wrapper]), wrapper
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                return list(value), key
        raise MemoryStoreError(f"记忆结构无效：{path}（需要列表或含列表键的对象）")
    else:
        raise MemoryStoreError(f"记忆结构无效：{path}（需要记录列表）")
    for index, item in enumerate(items):
        _validate_item(item, f"{path} 第 {index + 1} 条")
    return items, wrapper


def _save_items(path: Path, items: list[dict], wrapper: str | None) -> None:
    data: Any = {wrapper: items} if wrapper else items
    write_json(path, data)


def _new_item(args: argparse.Namespace, today: date) -> dict:
    item: dict[str, Any] = {
        "id": _require_str(args.id, "--id", max_chars=MAX_ID_CHARS),
        "created_at": today.isoformat(),
        "review_count": 0,
        "correct_streak": 0,
        "interval_days": 1,
        "last_reviewed": None,
        "next_review": None,
        "mastered": False,
    }
    if args.word is not None:
        item["word"] = _require_str(args.word, "--word")
    if args.content is not None:
        item["content"] = _require_str(args.content, "--content")
    if args.exam is not None:
        item["exam"] = _require_str(args.exam, "--exam")
    if args.module is not None:
        item["module"] = _require_str(args.module, "--module")
    if args.note is not None:
        item["note"] = _require_str(args.note, "--note")
    if "word" not in item and "content" not in item and "question" not in item:
        raise ValueError("add 需要 --word 或 --content 提供记忆内容")
    return item


def cmd_add(args: argparse.Namespace) -> dict:
    today = _today(args.today)
    path, wrapper = _resolve_file(args.skill, args.file, args.memory_root)
    items, _ = _load_items(path, wrapper)
    new_item = _new_item(args, today)
    for index, existing in enumerate(items):
        if existing.get("id") == new_item["id"]:
            # 幂等更新：只刷新描述字段，保留复习状态。
            preserved_keys = {
                "created_at",
                "review_count",
                "correct_streak",
                "interval_days",
                "last_reviewed",
                "next_review",
                "mastered",
                "ease_factor",
            }
            merged = {k: v for k, v in existing.items() if k in preserved_keys}
            merged.update({k: v for k, v in new_item.items() if k not in preserved_keys})
            _validate_item(merged, f"{path} 第 {index + 1} 条（更新后）")
            items[index] = merged
            _save_items(path, items, wrapper)
            return merged
    items.append(new_item)
    _save_items(path, items, wrapper)
    return new_item


def cmd_due(args: argparse.Namespace) -> dict:
    today = _today(args.today)
    path, wrapper = _resolve_file(args.skill, args.file, args.memory_root)
    items, _ = _load_items(path, wrapper)
    pool = []
    for item in items:
        state = MemoryState.from_item(item)
        if state.mastered and not args.all:
            continue
        if args.weak_only and state.correct_streak > WEAK_STREAK_THRESHOLD:
            continue
        if not args.all:
            if not _is_due(item, today):
                continue
        pool.append(item)
    ranked = sort_for_review(pool, today)
    limit = max(0, args.limit)
    selected = [enrich_item(item, today) for item in ranked[:limit]]
    return {"date": today.isoformat(), "total_due": len(ranked), "count": len(selected), "items": selected}


def cmd_grade(args: argparse.Namespace) -> dict:
    today = _today(args.today)
    path, wrapper = _resolve_file(args.skill, args.file, args.memory_root)
    items, _ = _load_items(path, wrapper)
    for index, item in enumerate(items):
        if item.get("id") != args.id:
            continue
        updated = schedule_review(item, quality=args.quality, today=today)
        _validate_item(updated, f"{path} 第 {index + 1} 条（grade 后）")
        items[index] = updated
        _save_items(path, items, wrapper)
        return updated
    raise MemoryStoreError(f"未找到 id 为 {args.id!r} 的记忆：{path}")


def cmd_status(args: argparse.Namespace) -> dict:
    today = _today(args.today)
    path, wrapper = _resolve_file(args.skill, args.file, args.memory_root)
    items, _ = _load_items(path, wrapper)
    mastered = 0
    due = 0
    new = 0
    weak = 0
    for item in items:
        state = MemoryState.from_item(item)
        if state.mastered:
            mastered += 1
            continue
        if state.review_count == 0:
            new += 1
        if state.correct_streak <= WEAK_STREAK_THRESHOLD:
            weak += 1
        if _is_due(item, today):
            due += 1
    weakest = sorted(
        (item for item in items if not MemoryState.from_item(item).mastered),
        key=lambda item: (
            item.get("correct_streak", 0),
            -(item.get("review_count", 0)),
            item.get("next_review") or "9999-99-99",
        ),
    )[:5]
    return {
        "skill": args.skill,
        "file": path.name,
        "date": today.isoformat(),
        "total": len(items),
        "mastered": mastered,
        "active": len(items) - mastered,
        "new": new,
        "due": due,
        "weak": weak,
        "weakest_ids": [item.get("id") for item in weakest],
    }


def cmd_remove(args: argparse.Namespace) -> dict:
    path, wrapper = _resolve_file(args.skill, args.file, args.memory_root)
    items, _ = _load_items(path, wrapper)
    kept = [item for item in items if item.get("id") != args.id]
    if len(kept) == len(items):
        raise MemoryStoreError(f"未找到 id 为 {args.id!r} 的记忆：{path}")
    _save_items(path, kept, wrapper)
    return {"removed": args.id, "remaining": len(kept)}


def _format_item_brief(item: dict) -> str:
    label = item.get("word") or item.get("content") or item.get("id", "?")
    if isinstance(label, str) and len(label) > 40:
        label = label[:37] + "..."
    meta = []
    if item.get("exam"):
        meta.append(str(item["exam"]))
    if item.get("module"):
        meta.append(str(item["module"]))
    suffix = f"（{'/'.join(meta)}）" if meta else ""
    return f"{item.get('id')}{suffix}: {label}"


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m learning_agent.memory.cli",
        description=(
            "确定性内容记忆 CLI：add/due/grade/status/remove。"
            "复习状态只经此读写；--memory-root/--json 等选项放在子命令之后。"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser, *, with_file: bool = False) -> None:
        p.add_argument("--skill", required=True, choices=CONTENT_SKILLS)
        if with_file:
            p.add_argument("--file", choices=sorted(TEXT_FILE_ALIASES), help="text-memorizer 存储文件")
        p.add_argument("--memory-root", type=Path, default=None, help="memory 目录（默认 ./memory）")
        p.add_argument("--json", action="store_true", help="JSON 输出")
        p.add_argument("--today", help="覆盖今天日期 YYYY-MM-DD（测试/回放用）")

    p_add = subparsers.add_parser("add", help="新增或幂等更新一条记忆")
    common(p_add, with_file=True)
    p_add.add_argument("--id", required=True)
    p_add.add_argument("--word", help="单词（word-deep-dive）")
    p_add.add_argument("--content", help="知识点/题目内容")
    p_add.add_argument("--exam", help="绑定考试，如 六级")
    p_add.add_argument("--module", help="文本记忆模块名")
    p_add.add_argument("--note", help="备注（释义、答案要点等）")
    p_add.set_defaults(func=cmd_add)

    p_due = subparsers.add_parser("due", help="按优先级抽取到期项")
    common(p_due, with_file=True)
    p_due.add_argument("--limit", type=int, default=DEFAULT_DUE_LIMIT)
    p_due.add_argument("--all", action="store_true", help="忽略间隔，包含全部未掌握项")
    p_due.add_argument("--weak-only", action="store_true", help=f"只取 correct_streak <= {WEAK_STREAK_THRESHOLD} 的薄弱项")
    p_due.set_defaults(func=cmd_due)

    p_grade = subparsers.add_parser("grade", help="记录一次复习结果并推进间隔")
    common(p_grade, with_file=True)
    p_grade.add_argument("--id", required=True)
    quality = p_grade.add_mutually_exclusive_group(required=True)
    quality.add_argument("--correct", action="store_true", help="自评正确（等价 quality=5）")
    quality.add_argument("--wrong", action="store_true", help="自评错误（等价 quality=1，重置间隔）")
    quality.add_argument("--quality", type=int, choices=range(0, 6), help="SM-2 quality 0-5")
    p_grade.set_defaults(func=cmd_grade)

    p_status = subparsers.add_parser("status", help="记忆统计摘要")
    common(p_status, with_file=True)
    p_status.set_defaults(func=cmd_status)

    p_remove = subparsers.add_parser("remove", help="按 id 删除一条记忆")
    common(p_remove, with_file=True)
    p_remove.add_argument("--id", required=True)
    p_remove.set_defaults(func=cmd_remove)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.memory_root is None:
        args.memory_root = default_memory_root()
    if getattr(args, "quality", None) is None:
        if getattr(args, "correct", False):
            args.quality = 5
        elif getattr(args, "wrong", False):
            args.quality = 1
    try:
        result = args.func(args)
    except (MemoryStoreError, ValueError) as exc:
        print(f"ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(result)
    else:
        _print_text(args, result)
    return 0


def _print_text(args: argparse.Namespace, result: dict) -> None:
    command = args.command
    if command == "add":
        print(f"已存入：{_format_item_brief(result)}")
        print(f"复习状态：新学，next_review={result.get('next_review') or '待首次复习'}")
    elif command == "due":
        print(f"到期复习：共 {result['total_due']} 条，本轮抽取 {result['count']} 条（{result['date']}）")
        for index, item in enumerate(result["items"], 1):
            print(f"  {index}. {_format_item_brief(item)}  连击={item.get('correct_streak', 0)}")
    elif command == "grade":
        print(
            f"已记录：id={result['id']} quality={args.quality} "
            f"streak={result['correct_streak']} interval={result['interval_days']}d "
            f"next={result['next_review']}"
        )
    elif command == "status":
        print(
            f"[{result['skill']}/{result['file']}] 总计 {result['total']} | "
            f"已掌握 {result['mastered']} | 待复习 {result['due']} | 新学 {result['new']} | 薄弱 {result['weak']}"
        )
        if result["weakest_ids"]:
            print(f"最薄弱：{', '.join(map(str, result['weakest_ids']))}")
    elif command == "remove":
        print(f"已删除 {result['removed']}，剩余 {result['remaining']} 条")


if __name__ == "__main__":
    raise SystemExit(main())
