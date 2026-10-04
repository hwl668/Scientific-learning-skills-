"""Append regression cases (mostly former routing failures) to routing_cases.jsonl.

Usage::

    python evals/bench/append_regression.py            # uses the picked list below
    python evals/bench/append_regression.py --dry-run  # print without appending
"""

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BENCH_CASES_PATH = PROJECT_ROOT / "evals/bench/dev.synthetic.jsonl"
ROUTING_CASES_PATH = PROJECT_ROOT / "data/routing_cases.jsonl"

CATEGORY = {
    "zero-base-learning": "zero",
    "fuzzy-understanding": "fuzzy",
    "deepening-learning": "deep",
    "problem-solving": "problem",
    "mistake-review": "mistake",
    "word-deep-dive": "word",
    "text-memorizer": "text",
    "study-plan-builder": "plan",
}

# 回归集补充：优先收录曾路由失败/被纠正标签的题（修复的守卫），再加覆盖面补充。
PICKED = [
    "zb-001", "zb-002", "zb-004", "zb-006", "zb-011", "zb-013", "zb-019",
    "fz-001", "fz-004", "fz-006", "fz-007", "fz-011", "fz-014",
    "ps-005", "ps-006", "ps-007", "ps-009", "ps-011", "ps-013", "ps-015", "ps-018", "ps-020",
    "ps-016",
    "mr-003", "mr-008", "mr-014",
    "dp-005", "dp-010",
    "wd-005",
    "tm-005",
    "sp-005",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    bench = {
        case["id"]: case
        for case in (
            json.loads(line)
            for line in BENCH_CASES_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }

    existing = ROUTING_CASES_PATH.read_text(encoding="utf-8")
    existing_texts = {json.loads(line)["text"] for line in existing.splitlines() if line.strip()}

    lines = []
    for case_id in PICKED:
        case = bench.get(case_id)
        if case is None:
            print(f"WARNING bench case {case_id} not found in {BENCH_CASES_PATH.name}")
            continue
        if case["text"] in existing_texts:
            continue
        entry = {
            "text": case["text"],
            "skill": case["intended_skill"],
            "category": CATEGORY[case["intended_skill"]],
            "from": "bench-v0.1",
        }
        lines.append(json.dumps(entry, ensure_ascii=False))

    if args.dry_run:
        print("\n".join(lines))
        print(f"dry-run: would append {len(lines)} cases")
        return 0
    with ROUTING_CASES_PATH.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"appended {len(lines)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
