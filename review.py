#!/usr/bin/env python3
"""Scientific Learning Skills — 复习进度面板

读取 memory/ 下所有内容记忆型 Skill 的数据，
展示到期复习数、掌握率、薄弱项排行。
只依赖 Python 标准库。
"""

import math
from datetime import date
from pathlib import Path

from learning_agent.memory.scheduler import (
    MAX_CORRECT_STREAK,
    MAX_EASE_FACTOR,
    MAX_INTERVAL_DAYS,
    MAX_REVIEW_COUNT,
    enrich_item,
    sort_for_review,
)
from learning_agent.memory.store import MemoryStoreError, read_json

# ── 终端颜色 ──────────────────────────────────────────────
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BLUE = "\033[0;34m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"

PROJECT_ROOT = Path(__file__).resolve().parent
MEMORY_ROOT = PROJECT_ROOT / "memory"
MAX_TEXT_FIELD_CHARS = 100_000


def _validate_memory_items(items, path):
    """Reject type-confused memory records before scheduler arithmetic."""

    for index, item in enumerate(items):
        location = f"{path} 第 {index + 1} 条"
        if not isinstance(item, dict):
            raise MemoryStoreError(f"记忆结构无效：{location} 必须是 JSON 对象")
        for field in ("review_count", "correct_streak"):
            value = item.get(field, 0)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise MemoryStoreError(f"记忆结构无效：{location} 的 {field} 必须是非负整数")
            limit = MAX_REVIEW_COUNT if field == "review_count" else MAX_CORRECT_STREAK
            if value > limit:
                raise MemoryStoreError(f"记忆结构无效：{location} 的 {field} 超过上限 {limit}")
        if "interval_days" in item:
            value = item["interval_days"]
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise MemoryStoreError(f"记忆结构无效：{location} 的 interval_days 必须是正整数")
            if value > MAX_INTERVAL_DAYS:
                raise MemoryStoreError(
                    f"记忆结构无效：{location} 的 interval_days 超过上限 {MAX_INTERVAL_DAYS}"
                )
        if "ease_factor" in item:
            value = item["ease_factor"]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or value <= 0
                or value > MAX_EASE_FACTOR
            ):
                raise MemoryStoreError(f"记忆结构无效：{location} 的 ease_factor 必须是有限正数")
        if "mastered" in item and not isinstance(item["mastered"], bool):
            raise MemoryStoreError(f"记忆结构无效：{location} 的 mastered 必须是布尔值")
        for field in ("created_at", "last_reviewed", "next_review"):
            value = item.get(field)
            if value is None:
                continue
            if not isinstance(value, str):
                raise MemoryStoreError(f"记忆结构无效：{location} 的 {field} 必须是日期字符串或 null")
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise MemoryStoreError(
                    f"记忆结构无效：{location} 的 {field} 必须是 YYYY-MM-DD"
                ) from exc
        for field in ("id", "word", "content", "title", "question"):
            if field in item and not isinstance(item[field], str):
                raise MemoryStoreError(f"记忆结构无效：{location} 的 {field} 必须是字符串")
            if field in item and len(item[field]) > MAX_TEXT_FIELD_CHARS:
                raise MemoryStoreError(
                    f"记忆结构无效：{location} 的 {field} 超过 {MAX_TEXT_FIELD_CHARS} 字符"
                )
    return items

def load_words():
    """加载单词记忆数据"""
    path = MEMORY_ROOT / "word-deep-dive" / "words.json"
    data = read_json(path)
    if data is None:
        return []
    # 兼容两种结构：{"words": [...]} 或 [...]
    if isinstance(data, dict):
        if "words" not in data or not isinstance(data["words"], list):
            raise MemoryStoreError(f"单词记忆结构无效：{path}（需要列表或含 words 列表的对象）")
        data = data["words"]
    if not isinstance(data, list):
        raise MemoryStoreError(f"单词记忆结构无效：{path}（需要记录列表）")
    return _validate_memory_items(data, path)


def load_text_memory():
    """加载文本记忆数据"""
    items = []
    base = MEMORY_ROOT / "text-memorizer"
    for fname in ("questions.json", "weak_points.json"):
        path = base / fname
        data = read_json(path)
        if data is None:
            continue
        if isinstance(data, list):
            values = data
        elif isinstance(data, dict):
            values = list(data.values())
        else:
            raise MemoryStoreError(f"文本记忆结构无效：{path}（需要列表或对象）")
        items.extend(_validate_memory_items(values, path))
    return items


def load_analytical_memory():
    """加载分析记忆型 Skill 的数据（非间隔复习，仅统计）"""
    analytical_skills = [
        "zero-base-learning", "fuzzy-understanding", "deepening-learning",
        "problem-solving", "mistake-review", "study-plan-builder"
    ]
    stats = {}
    for skill in analytical_skills:
        skill_dir = MEMORY_ROOT / skill
        if not skill_dir.is_dir():
            continue
        files = list(skill_dir.glob("*.json")) + list(skill_dir.glob("*.md"))
        stats[skill] = len([f for f in files if f.name != "README.md"])
    return stats


# ── 统计计算 ──────────────────────────────────────────────

def calc_review_stats(items):
    """从记忆条目计算复习统计"""
    today = date.today()

    total = len(items)
    mastered = sum(1 for i in items if i.get("mastered") or i.get("correct_streak", 0) >= 5)
    active = total - mastered

    due_now = []
    for i in items:
        if i.get("mastered") or i.get("correct_streak", 0) >= 5:
            continue
        next_str = i.get("next_review")
        if next_str:
            try:
                next_date = date.fromisoformat(next_str)
                if next_date <= today:
                    due_now.append(i)
            except (ValueError, TypeError):
                # 格式异常视为到期
                due_now.append(i)
        else:
            # 无 next_review = 未复习过 = 到期
            due_now.append(i)

    due_now = sort_for_review(due_now, today)

    mastery_rate = (mastered / total * 100) if total > 0 else 0

    return {
        "total": total,
        "mastered": mastered,
        "active": active,
        "due_now": due_now,
        "mastery_rate": mastery_rate,
    }


def find_weakest(items, n=10):
    """找出薄弱项 TOP N（correct_streak 最低、review_count 最高但未掌握的）"""
    active_items = [
        i for i in items
        if not (i.get("mastered") or i.get("correct_streak", 0) >= 5)
    ]
    active_items = sort_for_review(active_items)
    return active_items[:n]


# ── 输出渲染 ──────────────────────────────────────────────

def print_header(title):
    print()
    print(f"{BOLD}{CYAN}{'='*50}{NC}")
    print(f"{BOLD}{CYAN}  {title}{NC}")
    print(f"{BOLD}{CYAN}{'='*50}{NC}")
    print()


def print_bar(label, value, total, color=GREEN):
    """简单的文本进度条"""
    pct = (value / total * 100) if total > 0 else 0
    bar_width = 20
    filled = int(bar_width * value / total) if total > 0 else 0
    bar_str = f"{color}{'█' * filled}{DIM}{'░' * (bar_width - filled)}{NC}"
    print(f"  {label:12s} {bar_str}  {color}{value}{NC}/{total}  ({pct:.0f}%)")


def print_review_section(label, items, get_name_fn):
    """打印一个 Skill 的复习统计"""
    if not items:
        return

    stats = calc_review_stats(items)
    skill_color = BLUE

    print()
    print(f"  {BOLD}{label}{NC}")

    print_bar("总进度", stats["mastered"], stats["total"])
    print(f"  {'到期复习':12s} {RED if stats['due_now'] else GREEN}{len(stats['due_now'])} 条{NC}")

    if stats["due_now"]:
        print()
        print(f"  {BOLD}📅 待复习（前 8 条）：{NC}")
        for i, item in enumerate(stats["due_now"][:8]):
            name = get_name_fn(item)
            streak = item.get("correct_streak", 0)
            next_r = item.get("next_review") or "从未复习"
            item = enrich_item(item)
            risk = item.get("forgetting_risk", 0)
            mastery = item.get("mastery_probability", 0)
            priority = item.get("review_priority", 0)
            streak_color = RED if streak == 0 else YELLOW
            print(f"    {i+1}. {name}")
            print(f"       {DIM}正确连击 {streak_color}{streak}{DIM} · 下次复习 {next_r} · 掌握 {mastery:.0%} · 遗忘风险 {risk:.0%} · 优先级 {priority:.0%}{NC}")

    # 薄弱项
    weak = find_weakest(items)
    if weak:
        print()
        print(f"  {BOLD}🔴 薄弱项 TOP 5：{NC}")
        for i, item in enumerate(weak[:5]):
            name = get_name_fn(item)
            streak = item.get("correct_streak", 0)
            reviews = item.get("review_count", 0)
            item = enrich_item(item)
            mastery = item.get("mastery_probability", 0)
            priority = item.get("review_priority", 0)
            print(f"    {i+1}. {name}")
            print(f"       {DIM}正确 {RED}{streak}{DIM} 次 · 复习 {reviews} 次 · 掌握 {mastery:.0%} · 优先级 {priority:.0%}{NC}")


def get_word_name(item):
    return item.get("word", item.get("content", item.get("id", "?")))


def get_text_name(item):
    label = item.get("title", item.get("content", item.get("id", item.get("question", "?"))))
    return str(label)[:40]


def print_analytical_section(stats):
    """打印分析记忆概况"""
    if not stats:
        return
    print()
    print(f"  {BOLD}分析记忆{NC} (不参与间隔复习)：")
    for skill, count in sorted(stats.items()):
        name_map = {
            "zero-base-learning": "零基础教学",
            "fuzzy-understanding": "模糊理解诊断",
            "deepening-learning": "深化学习",
            "problem-solving": "解题方法",
            "mistake-review": "错题复盘",
            "study-plan-builder": "学习计划",
        }
        label = name_map.get(skill, skill)
        signal = f"{GREEN}{count} 条记录{NC}" if count > 0 else f"{DIM}无数据{NC}"
        print(f"    {label:12s} → {signal}")


def print_summary(all_items):
    """打印跨 Skill 汇总"""
    print()
    print(f"{BOLD}{CYAN}{'='*50}{NC}")
    print(f"{BOLD}{CYAN}  跨 Skill 汇总{NC}")
    print(f"{BOLD}{CYAN}{'='*50}{NC}")
    print()

    stats = calc_review_stats(all_items) if all_items else {"total": 0, "mastered": 0, "active": 0, "due_now": [], "mastery_rate": 0}

    print_bar("全部掌握率", stats["mastered"], stats["total"])
    print(f"  {'到期复习':12s} {RED}{len(stats['due_now'])}{NC} 条")
    print(f"  {'已掌握':12s} {GREEN}{stats['mastered']}{NC} 条")

    # 各 Skill 来源分布
    print()
    print(f"  {DIM}数据来源：{NC}")
    word_items = load_words()
    text_items = load_text_memory()
    print(f"    word-deep-dive:  {len(word_items)} 词")
    print(f"    text-memorizer:  {len(text_items)} 条")


# ── 主入口 ──────────────────────────────────────────────────

def main():
    print_header("📊 学习复习状态面板")

    try:
        # 1. 单词记忆
        words = load_words()
        print_review_section("📝 单词记忆 (word-deep-dive)", words, get_word_name)

        # 2. 文本记忆
        texts = load_text_memory()
        print_review_section("📄 文本记忆 (text-memorizer)", texts, get_text_name)

        # 3. 分析记忆概况
        analytical_stats = load_analytical_memory()
        print_analytical_section(analytical_stats)

        # 4. 跨 Skill 汇总
        all_items = words + texts
        print_summary(all_items)
    except MemoryStoreError as exc:
        print(f"  {RED}[ERR]{NC} {exc}")
        print(f"  {YELLOW}未继续读取，避免把损坏数据误判为空并覆盖。请检查同目录的 .bak 备份。{NC}")
        return 1

    # 5. 提示
    print()
    print(f"  {DIM}在 AI 中说「复习单词」或「出题」→ 开始间隔复习{NC}")
    print(f"  {DIM}说「学习报告」→ 获取跨 Skill 薄弱点汇总{NC}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
