#!/usr/bin/env python3
"""Rule-based Cognitive Diagnosis Engine for Scientific Learning Skills.

The diagnosis engine identifies the learner's likely cognitive bottleneck
before a tutor starts explaining. It is a deterministic baseline over the six
card-point labels used by fuzzy-understanding.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = PROJECT_ROOT / "data" / "diagnosis_cases.jsonl"

DIAGNOSIS_LABELS = {
    "concept_confusion": {
        "name": "概念混淆",
        "explanation": "学习者把两个或多个概念、方法、场景混在一起，需要先做对比辨析。",
    },
    "symbol_not_understood": {
        "name": "符号不懂",
        "explanation": "学习者主要卡在符号、记号、量词、上下标或形式表达的含义上，需要逐符号翻译。",
    },
    "derivation_gap": {
        "name": "推导断裂",
        "explanation": "学习者知道结论或答案，但看不懂中间步骤为什么成立，需要补齐推理链。",
    },
    "missing_prerequisite": {
        "name": "前置知识缺失",
        "explanation": "学习者当前问题依赖某个尚未建立的基础概念，需要先补前置知识。",
    },
    "rote_no_transfer": {
        "name": "只会背不会迁移",
        "explanation": "学习者能复述模板或做熟悉例题，但换条件后不能独立迁移，需要变式训练。",
    },
    "formula_without_understanding": {
        "name": "公式会用但不知道为什么",
        "explanation": "学习者能计算或套公式，但不知道公式背后的直觉、来源或适用条件。",
    },
}

DEFAULT_LABEL = "missing_prerequisite"


@dataclass(frozen=True)
class DiagnosisResult:
    label: str
    name: str
    confidence: float
    evidence: tuple[str, ...]
    explanation: str
    secondary: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "name": self.name,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "explanation": self.explanation,
            "secondary": list(self.secondary),
        }


RULES: dict[str, tuple[str, ...]] = {
    "concept_confusion": (
        "分不清",
        "混淆",
        "区别",
        "差别",
        "关系",
        "什么时候用哪个",
        "哪个该用",
        "和.*有什么不同",
        "和.*有什么关系",
        "到底是.*还是",
    ),
    "symbol_not_understood": (
        "符号",
        "记号",
        "量词",
        "下标",
        "上标",
        "箭头",
        "不等号",
        "ε",
        "δ",
        "∀",
        "∃",
        "∑",
        "Σ",
        "∫",
        "lim",
        "\\|",
        "竖线",
        "Im\\(",
        "Ker\\(",
        "⊆",
        "这个.*什么意思",
        "谁先给",
    ),
    "derivation_gap": (
        "推导",
        "中间步骤",
        "这一步",
        "为什么推出",
        "为什么能推出",
        "怎么得到",
        "得到",
        "怎么变成",
        "从哪来",
        "证明看不懂",
        "跳步",
        "省略",
        "断了",
        "下一行",
        "等号.*怎么",
        "上一行.*下一行",
    ),
    "missing_prerequisite": (
        "前置",
        "基础没学",
        "没学过",
        "听不懂.*因为",
        "不知道.*是什么",
        "先学什么",
        "需要补什么",
        "导致.*听不懂",
        "变换.*是什么意思",
        "空间.*是什么意思",
        "概率.*基础",
    ),
    "rote_no_transfer": (
        "例题会",
        "换一道",
        "换题",
        "变式",
        "一换",
        "换条件",
        "模板会",
        "只会背",
        "背模板",
        "不会迁移",
        "照着会",
        "自己做不会",
        "题型一变",
        "见过就会",
        "没见过",
    ),
    "formula_without_understanding": (
        "会套公式",
        "套公式",
        "会用.*公式",
        "会算",
        "能算",
        "公式.*为什么",
        "公式背后的原理",
        "背后的原理",
        "不知道为什么",
        "不知道原理",
        "公式从哪来",
        "为什么可以这样算",
        "机械计算",
        "只会算",
    ),
}

PRIORITY = (
    "concept_confusion",
    "derivation_gap",
    "symbol_not_understood",
    "missing_prerequisite",
    "rote_no_transfer",
    "formula_without_understanding",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _match_patterns(text: str, patterns: tuple[str, ...]) -> list[str]:
    matches = []
    for pattern in patterns:
        if re.search(pattern, text, re.I):
            matches.append(pattern)
    return matches


def _score_text(text: str) -> dict[str, list[str]]:
    return {label: _match_patterns(text, patterns) for label, patterns in RULES.items()}


def diagnose(text: str) -> DiagnosisResult:
    """Diagnose the learner's likely cognitive bottleneck."""

    normalized = _normalize(text)
    if not normalized:
        meta = DIAGNOSIS_LABELS[DEFAULT_LABEL]
        return DiagnosisResult(
            label=DEFAULT_LABEL,
            name=meta["name"],
            confidence=0.2,
            evidence=("empty:fallback",),
            explanation=meta["explanation"],
        )

    scored = _score_text(normalized)
    ranked = sorted(
        ((label, len(matches), matches) for label, matches in scored.items() if matches),
        key=lambda item: (-item[1], PRIORITY.index(item[0])),
    )

    if ranked:
        label, match_count, matches = ranked[0]
        confidence = min(0.95, 0.55 + 0.15 * match_count)
        secondary = tuple(item[0] for item in ranked[1:3])
    else:
        label = DEFAULT_LABEL
        matches = ["fallback:missing-prerequisite"]
        confidence = 0.35
        secondary = ()

    meta = DIAGNOSIS_LABELS[label]
    return DiagnosisResult(
        label=label,
        name=meta["name"],
        confidence=round(confidence, 2),
        evidence=tuple(matches),
        explanation=meta["explanation"],
        secondary=secondary,
    )


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
            if "text" not in case or "label" not in case:
                raise ValueError(f"{path}:{line_no}: case must contain text and label")
            if case["label"] not in DIAGNOSIS_LABELS:
                raise ValueError(f"{path}:{line_no}: unknown diagnosis label {case['label']!r}")
            cases.append(case)
    return cases


def evaluate_cases(path: Path = DEFAULT_CASES_PATH) -> dict:
    cases = load_cases(path)
    results = []
    correct = 0
    for case in cases:
        predicted = diagnose(case["text"])
        ok = predicted.label == case["label"]
        correct += int(ok)
        results.append(
            {
                "text": case["text"],
                "expected": case["label"],
                "predicted": predicted.label,
                "ok": ok,
                "confidence": predicted.confidence,
                "evidence": list(predicted.evidence),
                "secondary": list(predicted.secondary),
            }
        )
    total = len(results)
    accuracy = correct / total if total else 0.0
    return {"total": total, "correct": correct, "accuracy": accuracy, "results": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose a learner's cognitive bottleneck.")
    parser.add_argument("text", nargs="?", help="用户学习问题")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--eval", action="store_true", help="evaluate diagnosis accuracy on diagnosis_cases.jsonl")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="path to diagnosis_cases.jsonl")
    parser.add_argument("--min-accuracy", type=float, default=0.85, help="minimum accuracy for --eval")
    args = parser.parse_args(argv)

    cases_path = Path(args.cases)

    if args.eval:
        report = evaluate_cases(cases_path)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"diagnosis accuracy: {report['correct']}/{report['total']} = {report['accuracy']:.1%}")
            misses = [r for r in report["results"] if not r["ok"]]
            if misses:
                print("misses:")
                for miss in misses:
                    print(f"- expected={miss['expected']} predicted={miss['predicted']} text={miss['text']}")
        return 0 if report["accuracy"] >= args.min_accuracy else 1

    if not args.text:
        parser.error("text is required unless --eval is used")

    result = diagnose(args.text)
    if args.json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"{result.label}\t{result.name}\tconfidence={result.confidence:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
