#!/usr/bin/env python3
"""Scientific Learning Skills — 复习进度面板

读取 memory/ 下所有内容记忆型 Skill 的数据，
展示到期复习数、掌握率、薄弱项排行。
只依赖 Python 标准库。
"""

import json
import os
from datetime import date, datetime
from pathlib import Path
from collections import defaultdict

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

# ── 数据读取 ──────────────────────────────────────────────

def read_json(path: Path):
    """读取 JSON 文件，不存在则返回 None"""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def load_words():
    """加载单词记忆数据"""
    path = MEMORY_ROOT / "word-deep-dive" / "words.json"
    data = read_json(path)
    if not data:
        return []
    # 兼容两种结构：{"words": [...]} 或 [...]
    if isinstance(data, dict):
        return data.get("words", [])
    return data if isinstance(data, list) else []


def load_text_memory():
    """加载文本记忆数据"""
    items = []
    base = MEMORY_ROOT / "text-memorizer"
    for fname in ("questions.json", "weak_points.json"):
        data = read_json(base / fname)
        if data and isinstance(data, list):
            items.extend(data)
        elif data and isinstance(data, dict):
            items.extend(data.values())
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

    # 按优先级排：streak=0 > 最早 next_review
    due_now.sort(key=lambda x: (
        0 if x.get("correct_streak", 0) == 0 else 1,
        x.get("next_review") or "0000-00-00"
    ))

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
    # 排序：streak 越低越薄弱，相同 streak 按 review_count 降序
    active_items.sort(key=lambda x: (
        x.get("correct_streak", 0),
        -(x.get("review_count", 0))
    ))
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
            streak_color = RED if streak == 0 else YELLOW
            print(f"    {i+1}. {name}")
            print(f"       {DIM}正确连击 {streak_color}{streak}{DIM} · 下次复习 {next_r}{NC}")

    # 薄弱项
    weak = find_weakest(items)
    if weak:
        print()
        print(f"  {BOLD}🔴 薄弱项 TOP 5：{NC}")
        for i, item in enumerate(weak[:5]):
            name = get_name_fn(item)
            streak = item.get("correct_streak", 0)
            reviews = item.get("review_count", 0)
            print(f"    {i+1}. {name}")
            print(f"       {DIM}正确 {RED}{streak}{DIM} 次 · 复习 {reviews} 次{NC}")


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

    # 5. 提示
    print()
    print(f"  {DIM}在 AI 中说「复习单词」或「出题」→ 开始间隔复习{NC}")
    print(f"  {DIM}说「学习报告」→ 获取跨 Skill 薄弱点汇总{NC}")
    print()


if __name__ == "__main__":
    main()
