# -*- coding: utf-8 -*-
"""Build evals/bench/test.public.jsonl from the MathDial dataset (CC BY-SA 4.0).

Honesty notes (must stay in the file header / docs):
- MathDial grounds dialogues in real (GSM8K) math problems; the student side is
  LLM-simulated and vetted by human teachers, the tutoring conversations are
  human-authored. We therefore label derived cases `half-real`, never `real`.
- The learner query below is OUR packaging: we frame the student's verified
  confusion as a self-contained question in Chinese around the (English) problem
  and the student's stated attempt. Confusion descriptions and ground-truth
  solutions come from MathDial teachers.
- gold.diagnosis is MathDial's `teacher_described_confusion`; gold.must_not_do
  encodes MathDial's pedagogical finding (scaffold, don't dump solutions).

Usage::

    python scripts/build_test_public.py --mathdial mathdial_test.tmp.jsonl
"""

import argparse
import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = PROJECT_ROOT / "evals" / "bench" / "test.public.jsonl"

CONCEPTUAL_HINTS = ("concept", "misunderstand", "misinterpret", "why", "understand")


def first_student_turn(conversation: str) -> str:
    parts = [p.strip() for p in conversation.split("|EOM|")]
    for part in parts:
        if part.lower().startswith("student"):
            return part.split(":", 1)[1].strip() if ":" in part else part
    return ""


def build_text(row: dict, framing: str) -> str:
    question = " ".join(row["question"].split())
    attempt = " ".join(first_student_turn(row["conversation"]).split())
    if framing == "mistake-review":
        return (
            f"这道题我做错了：{question}\n"
            f"我的做法是：{attempt}\n但结果不对。帮我看看哪一步错了？"
        )
    if framing == "problem-solving":
        return (
            f"这题怎么做：{question}\n"
            f"我目前做到：{attempt}\n再往下就卡住了，没有思路。"
        )
    if framing == "fuzzy-understanding":
        return (
            f"{question}\n"
            f"我的做法是：{attempt}\n"
            "这一步我能算出来，但不理解为什么要这么做，感觉没有真正懂。"
        )
    raise ValueError(framing)


def classify(row: dict, index: int) -> str:
    # 固定周期分布 6:2:2（mr/ps/fuzzy），贴近真实求助分布且保证三类都有覆盖。
    return ("mistake-review", "mistake-review", "mistake-review",
            "problem-solving", "fuzzy-understanding",
            "mistake-review", "mistake-review", "problem-solving",
            "mistake-review", "fuzzy-understanding")[index % 10]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mathdial", type=Path, required=True, help="path to mathdial test.jsonl")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20261003)
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.mathdial.open(encoding="utf-8") if line.strip()]
    # 同一 qid 可能出现多次（不同 scenario），按 qid 去重保证 case id 唯一。
    by_qid: dict = {}
    for row in rows:
        by_qid.setdefault(row["qid"], row)
    rows = list(by_qid.values())
    # 分层：按 self-correctness 平衡，覆盖不同 scenario。
    yes_rows = [r for r in rows if r.get("self-correctness") == "Yes"]
    no_rows = [r for r in rows if r.get("self-correctness") != "Yes"]
    rng = random.Random(args.seed)
    rng.shuffle(yes_rows)
    rng.shuffle(no_rows)
    half = args.count // 2
    picked = yes_rows[:half] + no_rows[: args.count - half]
    picked.sort(key=lambda r: r["qid"])

    cases = []
    for index, row in enumerate(picked):
        skill = classify(row, index)
        framing = {
            "mistake-review": "mistake-review",
            "problem-solving": "problem-solving",
            "fuzzy-understanding": "fuzzy-understanding",
        }[skill]
        confusion = row.get("teacher_described_confusion") or "（未标注混淆描述）"
        case = {
            "id": f"md-{row['qid']}",
            "text": build_text(row, framing),
            "intended_skill": skill,
            "subject": "math",
            "source": "half-real",
            "origin": f"MathDial#{row['qid']} (CC BY-SA 4.0)",
            "student_context": {
                "prior_knowledge": [row["student_profile"]],
                "notes": confusion,
            },
            "gold": {
                "skill": skill,
                "diagnosis": f"卡点（MathDial 教师标注）：{confusion}",
                "must_address": [
                    f"定位并纠正该卡点：{confusion}",
                    "最终解法需与 MathDial ground truth 一致",
                ],
                "must_not_do": [
                    "在学生未理解卡点之前直接给出完整答案（MathDial 教学发现：应先脚手架式引导）",
                ],
            },
        }
        cases.append(case)

    header_note = {
        "_provenance": (
            "Derived from MathDial (eth-nlped/mathdial, CC BY-SA 4.0): real GSM8K-grounded problems, "
            "human-teacher tutoring dialogues, LLM-simulated student turns vetted by teachers. "
            "Cases are half-real: our Chinese framing around the student's vetted confusion; "
            "gold.diagnosis = MathDial teacher_described_confusion. NOT real learner data."
        )
    }
    with OUT_PATH.open("w", encoding="utf-8") as f:
        f.write(json.dumps(header_note, ensure_ascii=False) + "\n")
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")
    print(f"wrote {len(cases)} cases -> {OUT_PATH}")


if __name__ == "__main__":
    main()
