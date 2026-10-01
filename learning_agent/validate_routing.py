#!/usr/bin/env python3
"""Routing-contract consistency validator.

路由知识目前有三个面向不同运行时的表达：

1. ``learning_agent.router``      —— 确定性 baseline 的字面触发词
2. ``skills/scientific-learning/SKILL.md`` 路由表 —— LLM 兜底入口的触发契约
3. ``RULES.md`` 决策树             —— 人读/LLM 共用的规范层

三者手工维护时最容易悄悄漂移：router 新增了触发词但路由表不知道，LLM 就会
和 Python baseline 给出不同分流。本校验器把「router 的每个字面触发词都必须
被路由表行或决策树短语覆盖」变成 CI 门禁；反向不强制（文档可以保留 router
尚未实现的示例短语），但要求所有子 skill 在三处都有条目。

用法::

    python -m learning_agent.validate_routing
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from learning_agent.router import EXAM_NAMES, SKILLS, routing_keyword_rules

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROUTER_SKILL_DIR = PROJECT_ROOT / "skills" / "scientific-learning"
DEFAULT_SKILL_TABLE = ROUTER_SKILL_DIR / "SKILL.md"
DEFAULT_RULES = PROJECT_ROOT / "RULES.md"
DEFAULT_WORD_SKILL = PROJECT_ROOT / "skills" / "word-deep-dive" / "SKILL.md"

TABLE_ROW_PATTERN = re.compile(r"^\|(.+)\|\s*`([a-z][a-z-]*)`\s*\|\s*$")
TREE_ARROW_PATTERN = re.compile(r"→\s*`?([a-z][a-z-]*)`?")
QUOTED_PHRASE_PATTERN = re.compile(r'[“"「]([^”"」]+)[”"」]')
EXAM_LINE_PATTERN = re.compile(r"支持的考试[:：](.+)")


def parse_routing_table(path: Path) -> dict[str, str]:
    """Return {skill: row text} from the scientific-learning routing table."""

    rows: dict[str, str] = {}
    for line_no, line in enumerate(_read(path).splitlines(), 1):
        match = TABLE_ROW_PATTERN.match(line.strip())
        if not match:
            continue
        features, skill = match.group(1).strip(), match.group(2)
        if skill == "路由到":  # header row
            continue
        if skill in rows:
            raise ValueError(f"{path}:{line_no}: duplicate routing row for {skill}")
        rows[skill] = features
    return rows


def parse_rules_tree(path: Path) -> dict[str, set[str]]:
    """Return {skill: quoted trigger phrases} from the RULES.md decision tree.

    树中触发词与目标 skill 可能在不同行（换行的 `→ skill`），所以逐行收集
    引号短语，遇到箭头行时把积累的短语归属到该 skill。
    """

    assignments: dict[str, set[str]] = {}
    pending: set[str] = set()
    in_fence = False
    for line in _read(path).splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            continue
        pending.update(QUOTED_PHRASE_PATTERN.findall(stripped))
        arrow = TREE_ARROW_PATTERN.search(stripped)
        if arrow:
            skill = arrow.group(1)
            assignments.setdefault(skill, set()).update(pending)
            pending.clear()
    return assignments


def parse_supported_exams(path: Path) -> set[str]:
    match = EXAM_LINE_PATTERN.search(_read(path))
    if not match:
        return set()
    return set(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", match.group(1)))


def collect_issues(
    skill_table_path: Path = DEFAULT_SKILL_TABLE,
    rules_path: Path = DEFAULT_RULES,
    word_skill_path: Path = DEFAULT_WORD_SKILL,
) -> list[str]:
    issues: list[str] = []
    table = parse_routing_table(skill_table_path)
    tree = parse_rules_tree(rules_path)
    keywords_by_skill = routing_keyword_rules()
    sub_skills = [skill for skill in SKILLS if skill != "scientific-learning"]

    for skill in sub_skills:
        if skill not in table:
            issues.append(f"路由表缺少 {skill} 的行（{skill_table_path}）")
        if skill not in tree:
            issues.append(f"RULES.md 决策树缺少 {skill} 分支")

    for skill, keywords in keywords_by_skill.items():
        doc_text = table.get(skill, "") + " " + " ".join(sorted(tree.get(skill, set())))
        for keyword in keywords:
            if keyword not in doc_text:
                issues.append(
                    f"router 触发词 {keyword!r}（{skill}）未被路由表或决策树覆盖；"
                    f"请同步 {skill_table_path.name} / {rules_path.name}"
                )

    # 路由表里的子 skill 必须真实存在，防止拼写漂移。
    for skill in table:
        if skill not in SKILLS:
            issues.append(f"路由表包含未知 skill {skill!r}（{skill_table_path}）")
    for skill in tree:
        if skill not in SKILLS:
            issues.append(f"RULES.md 决策树包含未知 skill {skill!r}（{rules_path}）")

    # word-deep-dive 的考试名单与 router regex 共享 EXAM_NAMES。
    supported = parse_supported_exams(word_skill_path)
    missing_exams = [exam for exam in EXAM_NAMES if exam not in supported]
    if missing_exams:
        issues.append(
            f"word-deep-dive「支持的考试」缺少 {', '.join(missing_exams)}"
            f"（router regex 接受它们；{word_skill_path}）"
        )
    return issues


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate routing-contract consistency.")
    parser.add_argument("--skill-table", type=Path, default=DEFAULT_SKILL_TABLE)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--word-skill", type=Path, default=DEFAULT_WORD_SKILL)
    args = parser.parse_args(argv)

    try:
        issues = collect_issues(args.skill_table, args.rules, args.word_skill)
    except (OSError, ValueError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    if issues:
        for issue in issues:
            print(f"ERROR {issue}", file=sys.stderr)
        print(f"Routing consistency failed: {len(issues)} issue(s)", file=sys.stderr)
        return 1
    covered = sum(len(keywords) for keywords in routing_keyword_rules().values())
    print(f"Routing consistency passed: {covered} router triggers covered, "
          f"{len(SKILLS) - 1} sub-skills present in table and decision tree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
