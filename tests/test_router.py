import unittest
from pathlib import Path

from learning_agent.router import DEFAULT_CASES_PATH, SKILLS, evaluate_cases, load_cases, route


class RouterTest(unittest.TestCase):
    def test_all_cases_use_known_skills(self):
        cases = load_cases(DEFAULT_CASES_PATH)
        self.assertGreaterEqual(len(cases), 50)
        for case in cases:
            self.assertIn(case["skill"], SKILLS)
            self.assertTrue(case["text"].strip())

    def test_routing_cases_accuracy(self):
        report = evaluate_cases(DEFAULT_CASES_PATH)
        self.assertGreaterEqual(report["accuracy"], 0.9)

    def test_mistake_takes_priority_over_problem(self):
        result = route("这题我做错了，答案不一样，帮我看看为什么")
        self.assertEqual(result.skill, "mistake-review")

    def test_word_memory_takes_priority(self):
        result = route("复习单词")
        self.assertEqual(result.skill, "word-deep-dive")

    def test_text_memory_takes_priority(self):
        result = route("出题")
        self.assertEqual(result.skill, "text-memorizer")

    def test_explicit_scientific_learning(self):
        result = route("/scientific-learning 矩阵乘法是什么？")
        self.assertEqual(result.skill, "scientific-learning")


if __name__ == "__main__":
    unittest.main()
