"""LearningSkillBench case loading and schema validation.

Bench case schema (JSONL, one case per line):

    required fields
      id              str, globally unique (e.g. "zb-001", "md-014")
      text            str, non-empty learner query
      intended_skill  one of the 8 sub-skills (router entry excluded)
      subject         str, non-empty (e.g. "calculus")
      source          one of "real" | "half-real" | "synthetic"

    optional fields
      gap_type         str, coarse卡点类型 label
      origin           str, provenance for real/half-real cases (e.g. "MathDial#17")
      student_context  {"prior_knowledge": [str, ...], "notes": str}
      gold             {"skill": str,                # must equal intended_skill
                        "learner_state": str,        # e.g. "representation_gap"
                        "diagnosis": str,            # the卡点 the tutor should find
                        "must_address": [str, ...],  # content a good reply must cover
                        "must_not_do": [str, ...]}   # anti-patterns to avoid
      post_test        {"isomorphic":   {"question": str, "reference_answer": str},
                        "near_transfer": {...},
                        "far_transfer":  {...}}

gold/post_test presence is optional (dev set is annotated progressively);
when present, validate_cases checks their structure so the judge can rely on it.
"""

from __future__ import annotations

import json
from pathlib import Path

from learning_agent.router import SKILLS

BENCH_SOURCES = ("real", "half-real", "synthetic")

SUB_SKILLS = tuple(skill for skill in SKILLS if skill != "scientific-learning")

REQUIRED_FIELDS = ("id", "text", "intended_skill", "subject", "source")
OPTIONAL_DICT_FIELDS = ("student_context", "gold", "post_test")
POST_TEST_TIERS = ("isomorphic", "near_transfer", "far_transfer")


class CaseValidationError(ValueError):
    """Raised when a bench case file violates the schema."""


def _field_errors(case: dict, where: str) -> list[str]:
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        value = case.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{where}: missing or empty required field {field!r}")

    skill = case.get("intended_skill")
    if isinstance(skill, str) and skill not in SUB_SKILLS:
        errors.append(
            f"{where}: intended_skill {skill!r} is not a sub-skill; expected one of {', '.join(SUB_SKILLS)}"
        )

    source = case.get("source")
    if isinstance(source, str) and source not in BENCH_SOURCES:
        errors.append(f"{where}: source {source!r} must be one of {', '.join(BENCH_SOURCES)}")

    for field in OPTIONAL_DICT_FIELDS:
        if field in case and not isinstance(case[field], dict):
            errors.append(f"{where}: {field} must be an object")

    gold = case.get("gold")
    if isinstance(gold, dict):
        if "skill" in gold and gold["skill"] != skill:
            errors.append(
                f"{where}: gold.skill {gold['skill']!r} conflicts with intended_skill {skill!r}"
            )
        if "diagnosis" in gold and (not isinstance(gold["diagnosis"], str) or not gold["diagnosis"].strip()):
            errors.append(f"{where}: gold.diagnosis must be a non-empty string")
        for list_field in ("must_address", "must_not_do"):
            if list_field in gold:
                items = gold[list_field]
                if not isinstance(items, list) or not items or not all(
                    isinstance(item, str) and item.strip() for item in items
                ):
                    errors.append(f"{where}: gold.{list_field} must be a non-empty list of strings")

    post_test = case.get("post_test")
    if isinstance(post_test, dict):
        if not post_test:
            errors.append(f"{where}: post_test must not be empty when present")
        for tier, item in post_test.items():
            if tier not in POST_TEST_TIERS:
                errors.append(
                    f"{where}: post_test tier {tier!r} must be one of {', '.join(POST_TEST_TIERS)}"
                )
                continue
            if not isinstance(item, dict):
                errors.append(f"{where}: post_test.{tier} must be an object")
                continue
            for key in ("question", "reference_answer"):
                value = item.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{where}: post_test.{tier}.{key} must be a non-empty string")

    return errors


def load_cases(path: Path) -> list[dict]:
    """Load and schema-check a bench JSONL file. Raises CaseValidationError."""

    path = Path(path)
    cases: list[dict] = []
    seen_ids: set[str] = set()
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            where = f"{path}:{line_no}"
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CaseValidationError(f"{where}: invalid JSON: {exc}") from exc
            if not isinstance(case, dict):
                raise CaseValidationError(f"{where}: case must be a JSON object")
            if all(key.startswith("_") for key in case):
                continue  # provenance/metadata line (e.g. dataset licence note)

            errors = _field_errors(case, where)
            case_id = case.get("id")
            if isinstance(case_id, str) and case_id.strip():
                if case_id in seen_ids:
                    errors.append(f"{where}: duplicate case id {case_id!r}")
                seen_ids.add(case_id)
            if errors:
                raise CaseValidationError("\n".join(errors))
            cases.append(case)
    if not cases:
        raise CaseValidationError(f"{path}: no cases found")
    return cases


def source_counts(cases: list[dict]) -> dict[str, int]:
    counts = {source: 0 for source in BENCH_SOURCES}
    for case in cases:
        counts[case["source"]] += 1
    return counts


def gold_coverage(cases: list[dict]) -> dict[str, int]:
    return {
        "gold": sum(1 for case in cases if isinstance(case.get("gold"), dict)),
        "post_test": sum(1 for case in cases if isinstance(case.get("post_test"), dict)),
        "total": len(cases),
    }
