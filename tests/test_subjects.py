import unittest

from learning_agent.subjects import DEFAULT_CASES_PATH, filter_cases, load_subject_cases, summarize_cases


class SubjectCasesTest(unittest.TestCase):
    def test_subject_cases_load(self):
        cases = load_subject_cases(DEFAULT_CASES_PATH)
        self.assertGreaterEqual(len(cases), 30)

    def test_required_subject_coverage(self):
        summary = summarize_cases(load_subject_cases(DEFAULT_CASES_PATH))
        required = {
            "calculus",
            "linear_algebra",
            "probability_statistics",
            "algorithms",
            "machine_learning",
            "csapp",
            "operating_systems",
            "computer_networks",
            "signals_systems",
            "automatic_control",
            "circuits",
            "mathematical_modeling",
            "research_competition",
        }
        self.assertTrue(required.issubset(summary["subjects"]))

    def test_filter_by_subject(self):
        cases = load_subject_cases(DEFAULT_CASES_PATH)
        ml_cases = filter_cases(cases, subject="machine_learning")
        self.assertTrue(ml_cases)
        self.assertTrue(all(case["subject"] == "machine_learning" for case in ml_cases))


if __name__ == "__main__":
    unittest.main()
