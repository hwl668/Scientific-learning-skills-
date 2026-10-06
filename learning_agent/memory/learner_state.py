#!/usr/bin/env python3
"""Lightweight cross-turn learner state (调研建议 #4：知识点 × 卡点 × 已用策略 × 验证结果).

Purpose: so the NEXT similar question can resume from the last strategy instead of
re-running the full diagnosis flow. This is a small deterministic table — not a
knowledge-tracing model, not a profile system. Closed-set gaps (the six diagnosis
labels) keep it verifiable.

Storage: ``memory/learner-state.json`` via the same integrity primitives as the
review memory (atomic write, .bak backup, corruption raises instead of silently
resetting user data).

Usage::

    python -m learning_agent.memory.learner_state record --topic 矩阵乘法 \
        --gap formula_without_understanding --strategy "基向量变换类比" --verified false
    python -m learning_agent.memory.learner_state get --topic 矩阵乘法
    python -m learning_agent.memory.learner_state list
    python -m learning_agent.memory.learner_state clear --topic 矩阵乘法
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from learning_agent.diagnosis import DIAGNOSIS_LABELS
from learning_agent.memory.store import MemoryStoreError, read_json, write_json

STATE_VERSION = 1
MAX_TOPIC_CHARS = 60
MAX_STRATEGY_CHARS = 80
MAX_NOTE_CHARS = 200
MAX_STRATEGIES = 10
MAX_NOTES = 5

GAP_CHOICES = tuple(DIAGNOSIS_LABELS)


def default_state_root() -> Path:
    return Path("memory")


def _today(args_today: str | None) -> str:
    if args_today:
        try:
            return date.fromisoformat(args_today).isoformat()
        except ValueError as exc:
            raise SystemExit(f"invalid --today {args_today!r}: {exc}") from exc
    return date.today().isoformat()


def _state_path(memory_root: Path) -> Path:
    return Path(memory_root) / "learner-state.json"


def _load(memory_root: Path) -> dict:
    data = read_json(_state_path(memory_root), default=None)
    if data is None:
        return {"version": STATE_VERSION, "topics": {}}
    if not isinstance(data, dict) or not isinstance(data.get("topics"), dict):
        raise MemoryStoreError(f"learner-state.json has an unexpected shape: {_state_path(memory_root)}")
    return data


def _require_str(value: str | None, field: str, *, max_chars: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"{field} must be a non-empty string")
    value = value.strip()
    if len(value) > max_chars:
        raise SystemExit(f"{field} exceeds {max_chars} chars")
    return value


def record_topic(
    memory_root: Path,
    topic: str,
    gap: str,
    *,
    strategy: str | None = None,
    verified: bool | None = None,
    note: str | None = None,
    today: str | None = None,
) -> dict:
    topic = _require_str(topic, "--topic", max_chars=MAX_TOPIC_CHARS)
    if gap not in GAP_CHOICES:
        raise SystemExit(f"--gap must be one of: {', '.join(GAP_CHOICES)}")
    today = _today(today)

    data = _load(memory_root)
    topic_entry = data["topics"].setdefault(topic, {"gaps": {}, "updated_at": today})
    gap_entry = topic_entry["gaps"].setdefault(
        gap,
        {"count": 0, "first_seen": today, "last_seen": today, "strategies_used": [], "verified": False, "notes": []},
    )
    gap_entry["count"] += 1
    gap_entry["last_seen"] = today
    if strategy:
        strategy = _require_str(strategy, "--strategy", max_chars=MAX_STRATEGY_CHARS)
        if strategy not in gap_entry["strategies_used"]:
            if len(gap_entry["strategies_used"]) >= MAX_STRATEGIES:
                gap_entry["strategies_used"].pop(0)
            gap_entry["strategies_used"].append(strategy)
    if verified is not None:
        gap_entry["verified"] = bool(verified)
    if note:
        note = _require_str(note, "--note", max_chars=MAX_NOTE_CHARS)
        if note not in gap_entry["notes"]:
            if len(gap_entry["notes"]) >= MAX_NOTES:
                gap_entry["notes"].pop(0)
            gap_entry["notes"].append(f"{today} {note}")
    topic_entry["updated_at"] = today

    write_json(_state_path(memory_root), data)
    return {"topic": topic, "gap": gap, "state": gap_entry}


def get_topic(memory_root: Path, topic: str) -> dict | None:
    topic = _require_str(topic, "--topic", max_chars=MAX_TOPIC_CHARS)
    data = _load(memory_root)
    return data["topics"].get(topic)


def list_topics(memory_root: Path) -> list[dict]:
    data = _load(memory_root)
    summary = []
    for topic, entry in sorted(data["topics"].items()):
        summary.append(
            {
                "topic": topic,
                "gaps": {
                    gap: {"count": g["count"], "verified": g["verified"], "last_seen": g["last_seen"]}
                    for gap, g in entry.get("gaps", {}).items()
                },
                "updated_at": entry.get("updated_at"),
            }
        )
    return summary


def clear_topic(memory_root: Path, topic: str | None, clear_all: bool = False) -> int:
    data = _load(memory_root)
    if clear_all:
        removed = len(data["topics"])
        data["topics"] = {}
    else:
        topic = _require_str(topic, "--topic", max_chars=MAX_TOPIC_CHARS)
        if topic not in data["topics"]:
            return 0
        del data["topics"][topic]
        removed = 1
    write_json(_state_path(memory_root), data)
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m learning_agent.memory.learner_state",
        description="轻量跨轮 learner state：知识点 × 卡点 × 已用策略 × 验证结果。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--memory-root", type=Path, default=None, help="memory 目录（默认 ./memory）")
        p.add_argument("--json", action="store_true", help="JSON 输出")
        p.add_argument("--today", help="覆盖今天日期 YYYY-MM-DD（测试/回放用）")

    p_record = subparsers.add_parser("record", help="记录一次卡点观察（幂等更新该主题该卡点）")
    p_record.add_argument("--topic", required=True)
    p_record.add_argument("--gap", required=True, choices=GAP_CHOICES)
    p_record.add_argument("--strategy", help="本次使用的修复策略（去重后保留最近 10 条）")
    p_record.add_argument("--verified", choices=("true", "false"), help="变式验证是否通过")
    p_record.add_argument("--note", help="补充说明（保留最近 5 条）")
    common(p_record)

    p_get = subparsers.add_parser("get", help="查看一个主题的卡点状态")
    p_get.add_argument("--topic", required=True)
    common(p_get)

    p_list = subparsers.add_parser("list", help="列出全部主题摘要")
    common(p_list)

    p_clear = subparsers.add_parser("clear", help="清除一个主题（--topic）或全部（--all）")
    p_clear.add_argument("--topic")
    p_clear.add_argument("--all", action="store_true")
    common(p_clear)

    args = parser.parse_args(argv)
    memory_root = args.memory_root or default_state_root()

    try:
        if args.command == "record":
            verified = None if args.verified is None else args.verified == "true"
            payload = record_topic(
                memory_root,
                args.topic,
                args.gap,
                strategy=args.strategy,
                verified=verified,
                note=args.note,
                today=args.today,
            )
        elif args.command == "get":
            payload = get_topic(memory_root, args.topic)
            if payload is None:
                print(f"no learner state for topic: {args.topic}")
                return 1
        elif args.command == "list":
            payload = {"topics": list_topics(memory_root)}
        elif args.command == "clear":
            if not args.all and not args.topic:
                parser.error("clear requires --topic or --all")
            removed = clear_topic(memory_root, args.topic, clear_all=args.all)
            payload = {"removed": removed}
        else:  # pragma: no cover - argparse guards this
            parser.error(f"unknown command {args.command!r}")
    except MemoryStoreError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.command == "list":
        topics = payload["topics"]
        if not topics:
            print("(learner state is empty)")
        for entry in topics:
            gaps = "；".join(
                f"{gap}×{g['count']}{'✓' if g['verified'] else ''}（{g['last_seen']}）"
                for gap, g in entry["gaps"].items()
            )
            print(f"{entry['topic']}: {gaps}")
    elif args.command == "clear":
        print(f"removed {payload['removed']} topic(s)")
    else:
        for gap, g in payload.get("gaps", {}).items():
            name = DIAGNOSIS_LABELS[gap]["name"]
            strategies = "、".join(g["strategies_used"]) or "（无记录）"
            flag = "已验证" if g["verified"] else "未验证"
            print(f"{name}（{gap}）：出现 {g['count']} 次，{flag}，最近 {g['last_seen']}")
            print(f"  已用策略：{strategies}")
            for line in g["notes"]:
                print(f"  - {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
