#!/usr/bin/env python3
"""Rule-based Skill Router for Scientific Learning Skills.

The router is a deterministic baseline: it maps a learner's raw question to the
most likely learning skill using keyword rules and conflict priorities.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = PROJECT_ROOT / "data" / "routing_cases.jsonl"

SKILLS = (
    "zero-base-learning",
    "fuzzy-understanding",
    "deepening-learning",
    "problem-solving",
    "mistake-review",
    "word-deep-dive",
    "text-memorizer",
    "study-plan-builder",
    "scientific-learning",
)

DEFAULT_SKILL = "zero-base-learning"


@dataclass(frozen=True)
class RouteResult:
    skill: str
    confidence: float
    matched_rules: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "skill": self.skill,
            "confidence": self.confidence,
            "matched_rules": list(self.matched_rules),
        }


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _contains_any(text: str, patterns: tuple[str, ...]) -> list[str]:
    return [pattern for pattern in patterns if pattern in text]


def _regex_any(text: str, patterns: tuple[str, ...]) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, re.I)]


def _looks_like_single_english_word(text: str) -> bool:
    cleaned = text.strip()
    return bool(re.fullmatch(r"!?[A-Za-z][A-Za-z'-]*(?:\s+(?:六级|四级|考研|雅思|托福|GRE|gre|专四|专八|高考))?", cleaned))


def _looks_like_english_word_comparison(text: str) -> bool:
    return bool(re.search(r"\b[a-z][a-z'-]+\s+和\s+[a-z][a-z'-]+\b.*(区别|辨析|不同)", text, re.I))


def _explicit_skill(text: str) -> RouteResult | None:
    for skill in SKILLS:
        if skill in text:
            return RouteResult(skill=skill, confidence=1.0, matched_rules=(f"explicit:{skill}",))
    return None


def route(text: str) -> RouteResult:
    """Route a learner question to a skill.

    Priority matters more than raw keyword count. For example, "做错了" with a
    full problem should route to mistake review, not general problem solving.
    """

    normalized = _normalize(text)
    if not normalized:
        return RouteResult(skill=DEFAULT_SKILL, confidence=0.2, matched_rules=("empty:fallback",))

    explicit = _explicit_skill(normalized)
    if explicit:
        return explicit

    if normalized.startswith("/scientific-learning") or "用 scientific-learning" in normalized:
        return RouteResult("scientific-learning", 1.0, ("explicit:scientific-learning",))

    word_memory = _contains_any(
        normalized,
        ("复习单词", "单词复习", "单词列表", "单词记忆状态", "删除单词", "查词"),
    )
    is_single_word = _looks_like_single_english_word(text)
    is_word_comparison = _looks_like_english_word_comparison(normalized)
    if word_memory or is_single_word or is_word_comparison:
        rules = tuple(f"word:{m}" for m in word_memory)
        if is_single_word:
            rules += ("word:single-english-word",)
        if is_word_comparison:
            rules += ("word:english-word-comparison",)
        return RouteResult("word-deep-dive", 0.95, rules)

    text_memory = _contains_any(
        normalized,
        ("帮我背", "帮我记", "抽背", "出题", "默写", "复习薄弱点", "全部复习", "关键词触发"),
    )
    if text_memory:
        return RouteResult("text-memorizer", 0.95, tuple(f"text-memory:{m}" for m in text_memory))

    plan_matches = _contains_any(
        normalized,
        ("学习计划", "复习计划", "复习安排", "路线图", "备考", "冲刺", "多久学完", "怎么学完", "自学", "每天", "每周", "通过考试", "短期补齐"),
    )
    if plan_matches and not _contains_any(normalized, ("这题", "错题", "做错", "答案")):
        return RouteResult("study-plan-builder", 0.9, tuple(f"plan:{m}" for m in plan_matches))

    mistake_matches = _contains_any(
        normalized,
        ("做错", "错题", "错在哪", "为什么错", "答案不一样", "标准答案", "正确答案", "粗心", "扣分", "错因", "漏掉", "复盘"),
    )
    if mistake_matches:
        return RouteResult("mistake-review", 0.95, tuple(f"mistake:{m}" for m in mistake_matches))

    deep_matches = _contains_any(
        normalized,
        ("讲透", "本质", "多角度", "更深入", "深入理解", "证明思路", "推导", "反例", "联系", "为什么真正", "还能怎么看", "为什么重要", "结构理解"),
    )
    deep_regex_matches = _regex_any(normalized, (r"为什么.+可以用于",))
    if deep_matches or deep_regex_matches:
        rules = tuple(f"deep:{m}" for m in deep_matches) + tuple(f"deep-regex:{m}" for m in deep_regex_matches)
        return RouteResult("deepening-learning", 0.85, rules)

    problem_matches = _contains_any(
        normalized,
        ("这题", "题目", "求解", "证明", "怎么做", "不会做", "卡住", "解题", "算不出来", "做不出来", "lim", "极限题"),
    )
    if problem_matches:
        return RouteResult("problem-solving", 0.9, tuple(f"problem:{m}" for m in problem_matches))

    fuzzy_matches = _contains_any(
        normalized,
        ("学过", "听过", "会算", "会背", "会套", "不理解", "看不懂", "分不清", "不会用", "云里雾里", "一看", "懵", "到底在干什么"),
    )
    if fuzzy_matches:
        return RouteResult("fuzzy-understanding", 0.9, tuple(f"fuzzy:{m}" for m in fuzzy_matches))

    zero_matches = _contains_any(
        normalized,
        ("是什么", "什么是", "第一次", "完全不懂", "零基础", "从零", "入门", "讲一下", "介绍一下"),
    )
    if zero_matches:
        return RouteResult("zero-base-learning", 0.85, tuple(f"zero:{m}" for m in zero_matches))

    question_matches = _regex_any(normalized, (r"^.+是什么[？?]?$", r"^什么是.+", r".+怎么理解[？?]?$"))
    if question_matches:
        return RouteResult("zero-base-learning", 0.65, tuple(f"zero-regex:{m}" for m in question_matches))

    return RouteResult(skill=DEFAULT_SKILL, confidence=0.4, matched_rules=("fallback:zero-base-learning",))


def load_cases(path: Path = DEFAULT_CASES_PATH) -> list[dict]:
    cases = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if "text" not in case or "skill" not in case:
                raise ValueError(f"{path}:{line_no}: case must contain text and skill")
            if case["skill"] not in SKILLS:
                raise ValueError(f"{path}:{line_no}: unknown skill {case['skill']!r}")
            cases.append(case)
    return cases


def evaluate_cases(path: Path = DEFAULT_CASES_PATH) -> dict:
    cases = load_cases(path)
    results = []
    correct = 0
    for case in cases:
        predicted = route(case["text"])
        ok = predicted.skill == case["skill"]
        correct += int(ok)
        results.append(
            {
                "text": case["text"],
                "expected": case["skill"],
                "predicted": predicted.skill,
                "ok": ok,
                "matched_rules": list(predicted.matched_rules),
            }
        )
    total = len(results)
    accuracy = correct / total if total else 0.0
    return {"total": total, "correct": correct, "accuracy": accuracy, "results": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Route a learner question to a Scientific Learning skill.")
    parser.add_argument("text", nargs="?", help="用户学习问题")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--eval", action="store_true", help="evaluate router accuracy on routing_cases.jsonl")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="path to routing_cases.jsonl")
    parser.add_argument("--min-accuracy", type=float, default=0.9, help="minimum accuracy for --eval")
    args = parser.parse_args(argv)

    cases_path = Path(args.cases)

    if args.eval:
        report = evaluate_cases(cases_path)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"routing accuracy: {report['correct']}/{report['total']} = {report['accuracy']:.1%}")
            misses = [r for r in report["results"] if not r["ok"]]
            if misses:
                print("misses:")
                for miss in misses:
                    print(f"- expected={miss['expected']} predicted={miss['predicted']} text={miss['text']}")
        return 0 if report["accuracy"] >= args.min_accuracy else 1

    if not args.text:
        parser.error("text is required unless --eval is used")

    result = route(args.text)
    if args.json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.skill)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
