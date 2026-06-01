#!/usr/bin/env python3
"""Subject Case Library utilities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from learning_agent.diagnosis import DIAGNOSIS_LABELS
from learning_agent.router import SKILLS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = PROJECT_ROOT / "data" / "subject_cases.jsonl"

REQUIRED_FIELDS = {"id", "subject", "scenario", "prompt", "skill", "diagnosis", "rubric"}


def load_subject_cases(path: Path = DEFAULT_CASES_PATH) -> list[dict]:
    cases = []
    seen_ids = set()
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            missing = REQUIRED_FIELDS - set(case)
            if missing:
                raise ValueError(f"{path}:{line_no}: missing fields: {', '.join(sorted(missing))}")
            if case["id"] in seen_ids:
                raise ValueError(f"{path}:{line_no}: duplicate id {case['id']}")
            if case["skill"] not in SKILLS:
                raise ValueError(f"{path}:{line_no}: unknown skill {case['skill']}")
            if case["diagnosis"] not in DIAGNOSIS_LABELS:
                raise ValueError(f"{path}:{line_no}: unknown diagnosis {case['diagnosis']}")
            seen_ids.add(case["id"])
            cases.append(case)
    return cases


def summarize_cases(cases: list[dict]) -> dict:
    subjects = {}
    skills = {}
    diagnoses = {}
    for case in cases:
        subjects[case["subject"]] = subjects.get(case["subject"], 0) + 1
        skills[case["skill"]] = skills.get(case["skill"], 0) + 1
        diagnoses[case["diagnosis"]] = diagnoses.get(case["diagnosis"], 0) + 1
    return {
        "total": len(cases),
        "subjects": dict(sorted(subjects.items())),
        "skills": dict(sorted(skills.items())),
        "diagnoses": dict(sorted(diagnoses.items())),
    }


def filter_cases(cases: list[dict], subject: str | None = None, skill: str | None = None) -> list[dict]:
    if subject:
        cases = [case for case in cases if case["subject"] == subject]
    if skill:
        cases = [case for case in cases if case["skill"] == skill]
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect the Subject Case Library.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH))
    parser.add_argument("--subject")
    parser.add_argument("--skill")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    cases = filter_cases(load_subject_cases(Path(args.cases)), subject=args.subject, skill=args.skill)

    if args.summary:
        payload = summarize_cases(cases)
    else:
        payload = cases

    if args.json or args.summary:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for case in cases:
            print(f"{case['id']}\t{case['subject']}\t{case['skill']}\t{case['prompt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
