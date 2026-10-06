#!/usr/bin/env python3
"""LearningSkillBench judge: Level-2 quality scores, TER, and Level-3 grading.

Reads a run directory produced by bench.runner, asks the judge model to score
each (case, condition) response against the frozen judge prompt, and writes
judgements.jsonl alongside. Also grades simulated-learner post-test answers
(learner.jsonl) when present.

TER (Targeted Explanation Ratio) is computed deterministically from the judge's
explanation-unit annotations:

    TER = (# units marked addresses_gap) / (# units)

The judge model should differ from the subject model (recorded in run.json so
reports can disclose it).

Usage::

    python -m learning_agent.bench.judge --run-id pilot20
    python -m learning_agent.bench.judge --run-id pilot20 --provider mock
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from learning_agent.bench.api import APIError, make_client
from learning_agent.bench.cases import load_cases
from learning_agent.bench.prompts import (
    JUDGE_SYSTEM_PROMPT_V2,
    POST_TEST_JUDGE_SYSTEM_PROMPT_V2,
    parse_strict_json,
)
from learning_agent.bench.runner import DEFAULT_OUTPUT_ROOT, file_sha256  # noqa: F401  (file_sha256 re-exported for tests)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def ter_from_units(units: list[dict]) -> tuple[float, int]:
    """TER = relevant units / total units. Returns (ter, n_units)."""

    n = len(units)
    if n == 0:
        return 0.0, 0
    relevant = sum(1 for unit in units if unit.get("addresses_gap") is True)
    return relevant / n, n


def build_transcript(record: dict, learner_record: dict | None) -> str:
    """Judge input: turn-1 response plus, in learner runs, the two-turn teaching."""

    if not learner_record:
        return record["response_text"]
    return (
        f"[第一轮]\n{record['response_text']}\n\n"
        f"[学习者的回答]\n{learner_record.get('learner_diag_reply', '')}\n\n"
        f"[第二轮]\n{learner_record.get('tutor_turn2_text', '')}"
    )


def judge_record(client, case: dict, response_text: str, max_tokens: int) -> dict:
    gold = case.get("gold") or {}
    gold_block = {**gold, "student_level": case.get("student_level", "（未标注）")}
    gold_block = json.dumps(gold_block, ensure_ascii=False) if gold_block else "（无 gold 标注）"
    user = (
        f"## Learner question\n{case['text']}\n\n"
        f"## Gold metadata\n{gold_block}\n\n"
        f"## Tutoring response to evaluate\n{response_text}"
    )
    budget = max_tokens
    for attempt in range(3):
        result = client.complete(JUDGE_SYSTEM_PROMPT_V2, user, max_tokens=budget)
        try:
            parsed = parse_strict_json(result["text"])
            break
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            truncated = result.get("stop_reason") == "max_tokens" or not result["text"].strip()
            if not truncated or attempt == 2:
                return {
                    "judge_parse_error": last_error,
                    "judge_stop_reason": result.get("stop_reason"),
                    "raw_text": result["text"][:1000],
                }
            budget *= 2  # reasoning models can spend the whole budget thinking; retry with more
    ter, n_units = ter_from_units(parsed.get("units", []))
    return {
        "scores": {k: parsed.get(k) for k in (
            "correctness",
            "diagnostic_precision",
            "mistake_location",
            "explanation_relevance",
            "no_reveal",
            "cognitive_load",
            "hint_quality",
            "misconception_handling",
            "transfer_quality",
        )},
        "diagnosis_found": parsed.get("diagnosis_found"),
        "ter": round(ter, 4),
        "n_units": n_units,
        "units": parsed.get("units", []),
        "notes": parsed.get("notes"),
        "judge_output_tokens": result["output_tokens"],
        "judge_stop_reason": result.get("stop_reason"),
    }


def grade_learner_record(client, case: dict, learner_record: dict, max_tokens: int) -> dict:
    post_test = case.get("post_test") or {}
    answers = learner_record.get("answers") or {}
    if answers.get("parse_error"):
        return {"post_test": {"error": "learner output was not valid JSON"}}
    by_tier = {a.get("tier"): a.get("answer", "") for a in answers.get("answers", []) if isinstance(a, dict)}
    gold = case.get("gold") or {}
    block = {
        "misconception": gold.get("diagnosis"),
        "tiers": [
            {
                "tier": tier,
                "question": item["question"],
                "reference_answer": item["reference_answer"],
                "student_answer": by_tier.get(tier, "（未作答）"),
            }
            for tier, item in post_test.items()
        ],
    }
    user = "Grade this simulated student's post-test:\n" + json.dumps(block, ensure_ascii=False, indent=2)
    budget = max_tokens
    for attempt in range(3):
        result = client.complete(POST_TEST_JUDGE_SYSTEM_PROMPT_V2, user, max_tokens=budget)
        try:
            parsed = parse_strict_json(result["text"])
            break
        except (ValueError, json.JSONDecodeError) as exc:
            truncated = result.get("stop_reason") == "max_tokens" or not result["text"].strip()
            if not truncated or attempt == 2:
                return {"post_test": {"error": f"judge parse failure: {exc}"}}
            budget *= 2
    tiers = parsed.get("tiers", {})
    return {
        "post_test": {
            tier: value.get("correct") for tier, value in tiers.items() if isinstance(value, dict)
        },
        "misconception_corrected": parsed.get("misconception_corrected"),
        "notes": parsed.get("notes"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Judge a LearningSkillBench run directory.")
    parser.add_argument("--run-id", help="run directory name under artifacts/bench/")
    parser.add_argument("--run-dir", type=Path, help="explicit run directory (overrides --run-id, for tests)")
    parser.add_argument("--provider", choices=("anthropic", "openai", "mock"))
    parser.add_argument("--model", help="judge model override (default: BENCH_MODEL / provider default)")
    parser.add_argument("--max-tokens", type=int, default=16384, help="judge output budget; reasoning models need headroom")
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args(argv)

    if not args.run_dir and not args.run_id:
        parser.error("either --run-id or --run-dir is required")
    run_dir = args.run_dir or (DEFAULT_OUTPUT_ROOT / args.run_id)
    run_config_path = run_dir / "run.json"
    responses_path = run_dir / "responses.jsonl"
    if not run_config_path.exists() or not responses_path.exists():
        print(f"ERROR {run_dir} does not contain run.json/responses.jsonl; run bench.runner first", file=sys.stderr)
        return 1

    run_config = json.loads(run_config_path.read_text(encoding="utf-8"))
    cases_file = Path(run_config["cases_file"])
    cases = {case["id"]: case for case in load_cases(cases_file)}

    try:
        provider = args.provider or ("mock" if args.mock else None)
        if provider is None:
            from learning_agent.bench.api import detect_provider

            provider = detect_provider()
        client = make_client(provider, args.model, mock=args.mock)
    except APIError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    judgements_path = run_dir / "judgements.jsonl"
    done: set[tuple[str, str]] = set()
    if judgements_path.exists():
        for line in judgements_path.open(encoding="utf-8"):
            line = line.strip()
            if line:
                record = json.loads(line)
                done.add((record["case_id"], record["condition"]))

    records = [json.loads(line) for line in responses_path.open(encoding="utf-8") if line.strip()]
    todo = [r for r in records if (r["case_id"], r["condition"]) not in done]
    print(
        f"judging run {args.run_id}: {len(todo)} to judge, {len(done)} already done, "
        f"judge model={client.model} (subject model={run_config.get('subject_model')})"
    )

    warnings = []
    if run_config.get("subject_model") == client.model:
        warnings.append("judge model equals subject model; disclose this in the report")

    learner_path = run_dir / "learner.jsonl"
    learner_records: dict[tuple[str, str], dict] = {}
    if learner_path.exists():
        for line in learner_path.open(encoding="utf-8"):
            line = line.strip()
            if line:
                record = json.loads(line)
                learner_records[(record["case_id"], record["condition"])] = record

    failures = 0
    with judgements_path.open("a", encoding="utf-8") as out:
        for index, record in enumerate(todo, 1):
            case = cases.get(record["case_id"])
            if case is None:
                print(f"[{index}/{len(todo)}] {record['case_id']}: case not found in {cases_file}", file=sys.stderr)
                failures += 1
                continue
            entry = {
                "case_id": record["case_id"],
                "condition": record["condition"],
                "subject_output_tokens": record.get("output_tokens"),
            }
            learner = learner_records.get((record["case_id"], record["condition"]))
            if learner and learner.get("turn2_output_tokens") is not None:
                entry["subject_output_tokens"] = (record.get("output_tokens") or 0) + learner["turn2_output_tokens"]
            try:
                entry.update(
                    judge_record(client, case, build_transcript(record, learner), args.max_tokens)
                )
                if learner:
                    entry.update(grade_learner_record(client, case, learner, args.max_tokens))
            except APIError as exc:
                failures += 1
                entry["judge_api_error"] = str(exc)
                print(f"[{index}/{len(todo)}] {record['case_id']}/{record['condition']}: FAILED {exc}", file=sys.stderr)
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")
            out.flush()
            if "judge_api_error" not in entry:
                scores = entry.get("scores") or {}
                print(
                    f"[{index}/{len(todo)}] {record['case_id']}/{record['condition']}: "
                    f"TER={entry.get('ter')} units={entry.get('n_units')} "
                    f"correctness={scores.get('correctness')}"
                )
            time.sleep(0.2)

    for warning in warnings:
        print(f"WARNING {warning}", file=sys.stderr)
    if failures:
        print(f"{failures} failure(s); re-run the same command to resume", file=sys.stderr)
        return 1
    print(f"done -> {judgements_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
