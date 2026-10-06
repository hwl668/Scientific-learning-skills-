#!/usr/bin/env python3
"""LearningSkillBench runner: three-condition tutoring responses, frozen to disk.

Conditions (docs/learning-skill-bench.md §1):
    base           — bare model, no teaching prompt
    generic-tutor  — frozen generic "good teacher" prompt (length-matched control)
    skills         — deterministic router → sub-skill SKILL.md + RULES.md as system prompt

Outputs (gitignored): artifacts/bench/<run-id>/
    run.json          — config fingerprint: models, prompt hashes, case-file hash, git rev
    responses.jsonl   — one record per (case, condition): raw text + token usage
    learner.jsonl     — (with --with-learner) simulated-learner post-test answers

Re-running the same --run-id skips (case, condition) pairs already on disk, so a
failed run can be resumed without double-spending API calls.

Usage::

    python -m learning_agent.bench.runner --cases evals/bench/dev.synthetic.jsonl \
        --ids zb-001,zb-002 --run-id pilot20
    python -m learning_agent.bench.runner --cases ... --mock --run-id mock-smoke
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from learning_agent.bench.api import APIError, make_client
from learning_agent.bench.cases import load_cases
from learning_agent.bench.prompts import (
    GENERIC_TUTOR_PROMPT_V1,
    LEARNER_DIAG_SYSTEM_PROMPT_V1,
    LEARNER_DIAG_USER_TEMPLATE_V1,
    LEARNER_POSTTEST_SYSTEM_PROMPT_V1,
    LEARNER_POSTTEST_USER_TEMPLATE_V1,
    TUTOR_TURN2_TEMPLATE_V1,
    build_post_test_questions,
    freeze_manifest,
    prompt_identity,
    parse_strict_json,
)
from learning_agent.router import route

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = PROJECT_ROOT / "skills"
RULES_PATH = PROJECT_ROOT / "RULES.md"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "bench"

CONDITIONS = ("base", "generic-tutor", "skills")


def git_rev() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def build_skills_system_prompt(case: dict) -> tuple[str, str]:
    """System prompt for the `skills` condition: routed sub-skill + RULES.md.

    Returns (prompt, routed_skill). Uses the deterministic router so the run is
    reproducible; misroutes are visible in the report rather than hidden.
    """

    routed = route(case["text"]).skill
    skill_path = SKILLS_DIR / routed / "SKILL.md"
    parts = [skill_path.read_text(encoding="utf-8").strip()]
    if RULES_PATH.exists():
        parts.append(RULES_PATH.read_text(encoding="utf-8").strip())
    return "\n\n---\n\n".join(parts), routed


def build_user_message(case: dict) -> str:
    return case["text"]


def get_system_prompt(case: dict, condition: str) -> tuple[str | None, str]:
    """(system prompt, routed skill) for a condition; empty routed skill if N/A."""

    if condition == "skills":
        return build_skills_system_prompt(case)
    if condition == "generic-tutor":
        return GENERIC_TUTOR_PROMPT_V1, ""
    return None, ""


def existing_keys(responses_path: Path) -> set[tuple[str, str]]:
    if not responses_path.exists():
        return set()
    keys = set()
    with responses_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            keys.add((record["case_id"], record["condition"]))
    return keys


def run_learner_stage(
    client,
    learner_client,
    cases: dict[str, dict],
    responses_path: Path,
    out_path: Path,
    max_tokens: int,
) -> int:
    """Level 3, two-turn protocol.

    Why two turns: the Skills condition follows "diagnose before explaining",
    so a single turn can legitimately end in diagnostic questions with no
    teaching content. The simulated learner first answers those diagnostic
    questions in persona, the SAME tutor (same condition prompt) teaches a
    second turn given the answers, and only then takes the post-test. This
    measures the methodology's deployment shape instead of punishing
    diagnosis-first behavior for the single-turn format.

    `client` is the SUBJECT model (drives turn-2 teaching); `learner_client`
    plays the student (diagnostic answers + post-test). They may differ — a
    weaker learner raises Level-3 discrimination on hard post-tests.
    """

    done = existing_keys(out_path)
    completed = 0
    records = [json.loads(line) for line in responses_path.open(encoding="utf-8") if line.strip()]
    for record in records:
        case = cases.get(record["case_id"])
        if case is None:
            continue  # run resumed with a narrower --ids subset; other cases aren't in scope
        post_test = case.get("post_test") or {}
        key = (record["case_id"], record["condition"])
        if key in done:
            continue
        gold = case.get("gold") or {}
        misconception = gold.get("diagnosis", "（无标注，按提问内容推断）")

        diag_user = LEARNER_DIAG_USER_TEMPLATE_V1.format(
            query=case["text"],
            misconception=misconception,
            tutor_response=record["response_text"],
        )
        diag = learner_client.complete(LEARNER_DIAG_SYSTEM_PROMPT_V1, diag_user, max_tokens=max_tokens)
        learner_reply = diag["text"]

        system_prompt, _routed = get_system_prompt(case, record["condition"])
        turn2_user = TUTOR_TURN2_TEMPLATE_V1.format(
            query=case["text"],
            tutor_turn1=record["response_text"],
            learner_reply=learner_reply,
        )
        turn2 = client.complete(system_prompt, turn2_user, max_tokens=max_tokens)
        transcript = (
            f"[第一轮]\n{record['response_text']}\n\n"
            f"[学习者的回答]\n{learner_reply}\n\n"
            f"[第二轮]\n{turn2['text']}"
        )
        entry = {
            "case_id": record["case_id"],
            "condition": record["condition"],
            "learner_diag_reply": learner_reply,
            "tutor_turn2_text": turn2["text"],
            "turn2_output_tokens": turn2["output_tokens"],
            "turn2_stop_reason": turn2["stop_reason"],
        }
        if post_test:
            post_user = LEARNER_POSTTEST_USER_TEMPLATE_V1.format(
                query=case["text"],
                misconception=misconception,
                teaching_transcript=transcript,
                post_test_questions=build_post_test_questions(post_test),
            )
            post = learner_client.complete(LEARNER_POSTTEST_SYSTEM_PROMPT_V1, post_user, max_tokens=max_tokens)
            try:
                parsed = parse_strict_json(post["text"])
            except ValueError:
                parsed = {"answers": [], "parse_error": True, "raw": post["text"][:500]}
            entry["answers"] = parsed
            entry["post_test_raw"] = post["text"]
        out_path.open("a", encoding="utf-8").write(json.dumps(entry, ensure_ascii=False) + "\n")
        completed += 1
        time.sleep(0.2)
    return completed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the LearningSkillBench three-condition experiment.")
    parser.add_argument("--cases", required=True, type=Path, help="bench JSONL file")
    parser.add_argument("--ids", help="comma-separated case ids to include (default: all)")
    parser.add_argument("--limit", type=int, help="take the first N cases after filtering")
    parser.add_argument("--conditions", default=",".join(CONDITIONS), help=f"subset of {CONDITIONS}")
    parser.add_argument("--provider", choices=("anthropic", "openai", "mock"), help="default: auto-detect from env")
    parser.add_argument("--model", help="subject model override (default: BENCH_MODEL / provider default)")
    parser.add_argument("--learner-model", help="simulated-learner model override; a WEAKER model raises Level-3 "
                        "discrimination when post-tests hit a ceiling (default: same as subject)")
    parser.add_argument("--learner-provider", choices=("anthropic", "openai", "mock"),
                        help="provider for the simulated learner (default: same as --provider)")
    parser.add_argument("--judge-model", help="model name recorded for the (separate) judge step")
    parser.add_argument("--run-id", required=True, help="output directory name under artifacts/bench/")
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help="override output root (for tests)")
    parser.add_argument("--max-tokens", type=int, default=16384, help="per-call output budget; reasoning models spend it on thinking + answer")
    parser.add_argument("--with-learner", action="store_true", help="also run the Level 3 simulated-learner stage")
    parser.add_argument("--mock", action="store_true", help="offline mock client; output marked mock, not evidence")
    args = parser.parse_args(argv)

    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    unknown = [c for c in conditions if c not in CONDITIONS]
    if unknown:
        parser.error(f"unknown conditions {unknown}; expected subset of {CONDITIONS}")

    cases_list = load_cases(args.cases)
    if args.ids:
        wanted = {item.strip() for item in args.ids.split(",") if item.strip()}
        missing = wanted - {case["id"] for case in cases_list}
        if missing:
            parser.error(f"case ids not found in {args.cases}: {sorted(missing)}")
        cases_list = [case for case in cases_list if case["id"] in wanted]
    if args.limit:
        cases_list = cases_list[: args.limit]
    cases = {case["id"]: case for case in cases_list}
    if not cases:
        parser.error("no cases selected")

    try:
        provider = args.provider or ("mock" if args.mock else None)
        if provider is None:
            from learning_agent.bench.api import detect_provider

            provider = detect_provider()
        client = make_client(provider, args.model, mock=args.mock)
    except APIError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    run_dir = args.out_root / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    responses_path = run_dir / "responses.jsonl"

    run_config = {
        "run_id": args.run_id,
        "mock": args.mock or provider == "mock",
        "provider": client.protocol,
        "subject_model": client.model,
        "judge_model": args.judge_model,
        "learner_model": args.learner_model,
        "learner_provider": args.learner_provider,
        "cases_file": str(args.cases),
        "cases_file_sha256": file_sha256(args.cases),
        "case_ids": sorted(cases),
        "conditions": conditions,
        "max_tokens": args.max_tokens,
        "temperature": 0.0,
        "prompts": freeze_manifest(),
        "skills_condition_note": "system prompt = deterministic router -> skills/<skill>/SKILL.md + RULES.md",
        "git_rev": git_rev(),
        "with_learner": args.with_learner,
    }
    (run_dir / "run.json").write_text(
        json.dumps(run_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    done = existing_keys(responses_path)
    todo = [(case_id, condition) for case_id in cases for condition in conditions if (case_id, condition) not in done]
    print(
        f"run {args.run_id}: {len(cases)} cases x {len(conditions)} conditions "
        f"({len(todo)} to run, {len(done)} already done), provider={client.protocol}, model={client.model}"
    )

    failures = 0
    for index, (case_id, condition) in enumerate(todo, 1):
        case = cases[case_id]
        system_prompt, routed = get_system_prompt(case, condition)
        try:
            result = client.complete(system_prompt, build_user_message(case), max_tokens=args.max_tokens)
        except APIError as exc:
            failures += 1
            print(f"[{index}/{len(todo)}] {case_id}/{condition}: FAILED {exc}", file=sys.stderr)
            continue
        responses_path.open("a", encoding="utf-8").write(
            json.dumps(
                {
                    "case_id": case_id,
                    "condition": condition,
                    "routed_skill": routed,
                    "system_prompt_sha256": prompt_identity(system_prompt or "")["sha256"] if system_prompt else None,
                    "response_text": result["text"],
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "stop_reason": result["stop_reason"],
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        print(f"[{index}/{len(todo)}] {case_id}/{condition}: ok ({result.get('output_tokens')} out-tokens)")

    if args.with_learner:
        learner_client = client
        learner_model_name = client.model
        if args.learner_model or args.learner_provider:
            learner_provider = args.learner_provider or provider
            try:
                learner_client = make_client(learner_provider, args.learner_model, mock=args.mock)
                learner_model_name = learner_client.model
            except APIError as exc:
                print(f"ERROR learner client: {exc}", file=sys.stderr)
                return 1
            print(f"learner stage model: {learner_model_name} (subject: {client.model})")
        learner_path = run_dir / "learner.jsonl"
        completed = run_learner_stage(client, learner_client, cases, responses_path, learner_path, args.max_tokens)
        print(f"learner stage: {completed} new post-test answer sets -> {learner_path}")

    if failures:
        print(f"{failures} call(s) failed; fix credentials/network and re-run with the same --run-id to resume", file=sys.stderr)
        return 1
    print(f"done -> {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
