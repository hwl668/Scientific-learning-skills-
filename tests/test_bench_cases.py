"""Schema-validation tests for LearningSkillBench case files."""

import json
import tempfile
import unittest
from pathlib import Path

from learning_agent.bench.cases import CaseValidationError, gold_coverage, load_cases, source_counts

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEV_CASES = PROJECT_ROOT / "evals" / "bench" / "dev.synthetic.jsonl"
PUBLIC_CASES = PROJECT_ROOT / "evals" / "bench" / "test.public.jsonl"


def write_cases(cases: list[dict]) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    for case in cases:
        handle.write(json.dumps(case, ensure_ascii=False) + "\n")
    handle.close()
    return Path(handle.name)


def valid_case(**overrides) -> dict:
    case = {
        "id": "t-001",
        "text": "什么是极限？",
        "intended_skill": "zero-base-learning",
        "subject": "calculus",
        "source": "synthetic",
    }
    case.update(overrides)
    return case


class TestLoadCases(unittest.TestCase):
    def test_repo_files_pass_schema(self):
        for path in (DEV_CASES, PUBLIC_CASES):
            with self.subTest(path=path.name):
                cases = load_cases(path)
                self.assertGreater(len(cases), 0)

    def test_missing_required_field_rejected(self):
        path = write_cases([{"id": "t-001", "text": "hi", "source": "synthetic"}])
        with self.assertRaises(CaseValidationError):
            load_cases(path)

    def test_unknown_source_rejected(self):
        path = write_cases([valid_case(source="fabricated")])
        with self.assertRaises(CaseValidationError):
            load_cases(path)

    def test_unknown_skill_rejected(self):
        path = write_cases([valid_case(intended_skill="scientific-learning")])
        with self.assertRaises(CaseValidationError):
            load_cases(path)

    def test_duplicate_ids_rejected(self):
        path = write_cases([valid_case(), valid_case()])
        with self.assertRaises(CaseValidationError):
            load_cases(path)

    def test_provenance_metadata_line_skipped(self):
        path = write_cases([{"_provenance": "Derived from X"}, valid_case()])
        self.assertEqual(len(load_cases(path)), 1)

    def test_gold_skill_conflict_rejected(self):
        case = valid_case(gold={"skill": "problem-solving", "diagnosis": "x", "must_address": ["y"]})
        path = write_cases([case])
        with self.assertRaises(CaseValidationError):
            load_cases(path)

    def test_gold_must_address_must_be_list(self):
        case = valid_case(gold={"skill": "zero-base-learning", "diagnosis": "x", "must_address": "y"})
        path = write_cases([case])
        with self.assertRaises(CaseValidationError):
            load_cases(path)

    def test_post_test_requires_question_and_reference(self):
        case = valid_case(post_test={"isomorphic": {"question": "q"}})
        path = write_cases([case])
        with self.assertRaises(CaseValidationError):
            load_cases(path)

    def test_post_test_unknown_tier_rejected(self):
        case = valid_case(post_test={"random": {"question": "q", "reference_answer": "a"}})
        path = write_cases([case])
        with self.assertRaises(CaseValidationError):
            load_cases(path)

    def test_wellformed_gold_and_post_test_accepted(self):
        case = valid_case(
            gold={"skill": "zero-base-learning", "learner_state": "prior_missing",
                  "diagnosis": "d", "must_address": ["a"], "must_not_do": ["b"]},
            post_test={"isomorphic": {"question": "q", "reference_answer": "r"}},
        )
        path = write_cases([case])
        cases = load_cases(path)
        self.assertEqual(gold_coverage(cases), {"gold": 1, "post_test": 1, "total": 1})
        self.assertEqual(source_counts(cases), {"real": 0, "half-real": 0, "synthetic": 1})


if __name__ == "__main__":
    unittest.main()
