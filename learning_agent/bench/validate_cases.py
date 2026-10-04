#!/usr/bin/env python3
"""Bench case validation: schema gate + router-agreement gate.

Checks, in order:

1. Schema  — every case file parses, required fields present, gold/post_test
   well-formed when present, ids unique across files.
2. Routing — the deterministic router agrees with ``intended_skill`` on every
   case above a threshold (default 100% for the dev set: the bench doubles as
   the router regression corpus, so a disagreement is either a mislabeled case
   or a router regression — both must be resolved before release).

Usage::

    python -m learning_agent.bench.validate_cases
    python -m learning_agent.bench.validate_cases --cases evals/bench/dev.synthetic.jsonl
    python -m learning_agent.bench.validate_cases --min-routing-agreement 0.95
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from learning_agent.bench.cases import CaseValidationError, gold_coverage, load_cases, source_counts
from learning_agent.router import route

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = PROJECT_ROOT / "evals" / "bench"
DEFAULT_CASES = (BENCH_DIR / "dev.synthetic.jsonl", BENCH_DIR / "test.public.jsonl")


def routing_agreement(cases: list[dict]) -> tuple[int, list[dict]]:
    """Return (agreements, disagreement details) for the deterministic router."""

    agreements = 0
    disagreements: list[dict] = []
    for case in cases:
        predicted = route(case["text"])
        if predicted.skill == case["intended_skill"]:
            agreements += 1
        else:
            disagreements.append(
                {
                    "id": case["id"],
                    "intended_skill": case["intended_skill"],
                    "predicted_skill": predicted.skill,
                    "matched_rules": list(predicted.matched_rules),
                    "text": case["text"],
                }
            )
    return agreements, disagreements


def validate(paths: list[Path], min_agreement: float) -> tuple[bool, str]:
    lines: list[str] = []
    ok = True
    total_cases = 0
    total_agreements = 0

    try:
        per_path = [(path, load_cases(path)) for path in paths]
    except CaseValidationError as exc:
        return False, f"schema validation FAILED\n{exc}"

    seen_ids: dict[str, Path] = {}
    for path, cases in per_path:
        for case in cases:
            case_id = case["id"]
            if case_id in seen_ids:
                ok = False
                lines.append(f"ERROR duplicate case id {case_id!r} in {path.name} (first seen in {seen_ids[case_id].name})")
            seen_ids[case_id] = path

    for path, cases in per_path:
        counts = source_counts(cases)
        coverage = gold_coverage(cases)
        agreements, disagreements = routing_agreement(cases)
        total_cases += len(cases)
        total_agreements += agreements
        rate = agreements / len(cases) if cases else 0.0
        lines.append(
            f"{path.name}: {len(cases)} cases | sources real/half-real/synthetic = "
            f"{counts['real']}/{counts['half-real']}/{counts['synthetic']} | "
            f"gold {coverage['gold']}/{len(cases)}, post_test {coverage['post_test']}/{len(cases)} | "
            f"router agreement {agreements}/{len(cases)} = {rate:.0%}"
        )
        for disagreement in disagreements:
            lines.append(
                f"  DISAGREE [{disagreement['id']}] intended={disagreement['intended_skill']} "
                f"predicted={disagreement['predicted_skill']} rules={','.join(disagreement['matched_rules'])}"
            )

    if total_cases:
        overall = total_agreements / total_cases
        if overall < min_agreement:
            ok = False
            lines.append(
                f"ERROR router agreement {overall:.1%} below threshold {min_agreement:.0%}; "
                f"fix mislabeled cases or router regressions before release"
            )
    else:
        ok = False
        lines.append("ERROR no case files found")

    lines.insert(0, "bench case validation PASSED" if ok else "bench case validation FAILED")
    return ok, "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate LearningSkillBench case files.")
    parser.add_argument(
        "--cases",
        nargs="+",
        type=Path,
        default=[path for path in DEFAULT_CASES if path.exists()] or [BENCH_DIR / "dev.synthetic.jsonl"],
        help="bench JSONL files (default: dev.synthetic.jsonl + test.public.jsonl when present)",
    )
    parser.add_argument("--min-routing-agreement", type=float, default=1.0)
    args = parser.parse_args(argv)

    ok, message = validate(args.cases, args.min_routing_agreement)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
