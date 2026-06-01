import unittest

from learning_agent.diagnosis import (
    DEFAULT_CASES_PATH,
    DIAGNOSIS_LABELS,
    diagnose,
    evaluate_cases,
    load_cases,
)


class DiagnosisTest(unittest.TestCase):
    def test_all_cases_use_known_labels(self):
        cases = load_cases(DEFAULT_CASES_PATH)
        self.assertGreaterEqual(len(cases), 40)
        for case in cases:
            self.assertIn(case["label"], DIAGNOSIS_LABELS)
            self.assertTrue(case["text"].strip())

    def test_diagnosis_cases_accuracy(self):
        report = evaluate_cases(DEFAULT_CASES_PATH)
        self.assertGreaterEqual(report["accuracy"], 0.85)

    def test_symbol_not_understood(self):
        result = diagnose("ε-N 定义里 ε 和 N 到底谁先给？")
        self.assertEqual(result.label, "symbol_not_understood")
        self.assertGreaterEqual(result.confidence, 0.5)

    def test_derivation_gap(self):
        result = diagnose("证明里这一行为什么能推出下一行？")
        self.assertEqual(result.label, "derivation_gap")

    def test_formula_without_understanding(self):
        result = diagnose("矩阵乘法我会算，但不知道为什么要行乘列。")
        self.assertEqual(result.label, "formula_without_understanding")

    def test_result_has_explanation(self):
        result = diagnose("例题我会做，但换一道题就不会了。")
        self.assertEqual(result.name, "只会背不会迁移")
        self.assertTrue(result.explanation)
        self.assertTrue(result.evidence)


if __name__ == "__main__":
    unittest.main()
