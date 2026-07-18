import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from learning_agent.eval.runner import evaluate, evaluate_suite, load_jsonl_cases, main, render_markdown_report
from learning_agent.eval.scorers import STOP_MARKER, parse_file_meta, score_misconception


GOOD_CONCEPT = """
## 诊断
先确认两个问题：你卡在符号，还是不知道为什么需要这个定义？

## 直觉
可以想象你在不断靠近一堵墙，比如每次走剩下一半距离。

## 正式定义
定义：如果对任意 ε > 0，存在 N，使得 n > N 时满足 |a_n - L| < ε，则记为 lim a_n = L。

## 例题
例如 a_n = 1/n。
步骤 1. 选择 N。
步骤 2. 验证 n > N 时距离小于 ε。

## 常见误区
| 常见错误 | 为什么错 | 正确理解 |
|---|---|---|
| 以为 N 固定 | N 要跟 ε 变化 | 先给 ε，再找 N |
| 以为只需验证一个 ε | 定义要求任意 ε | 对每个正 ε 都要能找到 N |

## 变式
换成 a_n = 2/n 试试，检验你是否理解。

## 总结
关键是：极限定义在严格描述“任意精度都能最终靠近”。
"""


class EvalRunnerTest(unittest.TestCase):
    def test_evaluate_concept_text(self):
        result = evaluate(GOOD_CONCEPT, label="case")
        self.assertTrue(result["passed"])
        self.assertEqual(result["rubric"], "concept")

    def test_parse_baseline_marker(self):
        meta = parse_file_meta("<!-- rubric: baseline -->\nhello")
        self.assertTrue(meta["is_baseline"])
        self.assertEqual(meta["rubric"], "concept")

    def test_inline_baseline_marker_cannot_bypass_evaluation(self):
        result = evaluate("<!-- rubric: baseline -->\n只有一句空泛回答")
        self.assertFalse(result["is_baseline"])
        self.assertFalse(result["passed"])

        curated = evaluate(
            "<!-- rubric: baseline -->\n只有一句空泛回答",
            allow_inline_baseline=True,
        )
        self.assertTrue(curated["is_baseline"])

    def test_stop_marker_cannot_hide_forbidden_output(self):
        result = evaluate(GOOD_CONCEPT + STOP_MARKER + "\n加油！显然后面的推理可以省略。")
        self.assertFalse(result["style_gate_passed"])
        self.assertFalse(result["passed"])

        curated = evaluate(
            GOOD_CONCEPT + STOP_MARKER + "\n加油！",
            allow_stop_marker=True,
        )
        self.assertTrue(curated["style_gate_passed"])

    def test_p0_misconception_table_is_a_hard_gate(self):
        before, remainder = GOOD_CONCEPT.split("## 常见误区", 1)
        _table, after = remainder.split("## 变式", 1)
        result = evaluate(before + "## 变式" + after)

        self.assertGreaterEqual(result["total"], 14)
        self.assertFalse(result["p0_passed"])
        self.assertFalse(result["passed"])

    def test_evaluate_jsonl_suite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "suite.jsonl"
            path.write_text(
                json.dumps({"id": "concept-ok", "rubric": "concept", "text": GOOD_CONCEPT}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            results = evaluate_suite(path)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["passed"])

    def test_markdown_report(self):
        report = render_markdown_report([evaluate(GOOD_CONCEPT, label="case")])
        self.assertIn("# Eval Report", report)
        self.assertIn("| case | concept |", report)

    def test_misconception_table_counts_only_real_data_rows(self):
        one_error = """
## 常见误区
| 常见错误 | 为什么错 | 正确理解 |
|---|---|---|
| 把表头当内容 | 表头只是结构 | 只数数据行 |
"""
        two_errors = one_error + "| 把分隔线当内容 | 分隔线没有语义 | 排除 Markdown 分隔线 |\n"

        self.assertEqual(score_misconception(one_error)[0], 1)
        self.assertEqual(score_misconception(two_errors)[0], 2)

    def test_unrelated_table_cannot_earn_full_misconception_score(self):
        text = """
## 常见误区
请注意边界条件。

| 题号 | 难度 | 分值 |
|---|---|---|
| 1 | 易 | 2 |
| 2 | 难 | 4 |
"""
        self.assertEqual(score_misconception(text)[0], 1)

    def test_error_log_and_placeholder_rows_cannot_satisfy_p0(self):
        error_log = """
## 常见误区
| 错误码 | 时间 | 用户 |
|---|---|---|
| E001 | 10:00 | alice |
| E002 | 10:01 | bob |
"""
        placeholders = """
## 常见误区
| 常见错误 | 为什么错 | 正确理解 |
|---|---|---|
| [错误 1] | [原因 1] | [正解 1] |
| [错误 2] | [原因 2] | [正解 2] |
"""
        duplicate = """
## 常见误区
| 常见错误 | 为什么错 | 正确理解 |
|---|---|---|
| 忽略定义域 | 可能无定义 | 先检查定义域 |
| 忽略定义域 | 可能无定义 | 先检查定义域 |
"""

        self.assertLess(score_misconception(error_log)[0], 2)
        self.assertLess(score_misconception(placeholders)[0], 2)
        self.assertLess(score_misconception(duplicate)[0], 2)

    def test_unknown_rubric_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown rubric"):
            evaluate(GOOD_CONCEPT, rubric="not-a-rubric")

    def test_rubric_alias_is_canonicalized(self):
        result = evaluate(GOOD_CONCEPT, rubric="problem")
        self.assertEqual(result["rubric"], "problem-solving")

    def test_input_mode_uses_explicit_skill_rubric(self):
        output = io.StringIO()
        with redirect_stdout(output):
            main(
                [
                    "--input-text",
                    GOOD_CONCEPT,
                    "--skill",
                    "word-deep-dive",
                    "--report",
                    "json",
                ]
            )

        report = json.loads(output.getvalue())
        self.assertEqual(report["results"][0]["rubric"], "word")

    def test_all_baseline_suite_cannot_pass_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baseline-only.jsonl"
            path.write_text(
                json.dumps(
                    {"id": "excluded", "text": GOOD_CONCEPT, "baseline": True},
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                exit_code = main(["--suite", str(path), "--report", "json"])

        self.assertEqual(exit_code, 1)

    def test_jsonl_schema_validation(self):
        invalid_lines = {
            "array": "[]",
            "blank-text": json.dumps({"id": "blank", "text": "  "}),
            "bad-rubric": json.dumps({"id": "bad-rubric", "text": "content", "rubric": "unknown"}),
            "bad-baseline": json.dumps({"id": "bad-baseline", "text": "content", "baseline": "false"}),
        }
        with tempfile.TemporaryDirectory() as tmp:
            for name, line in invalid_lines.items():
                with self.subTest(name=name):
                    path = Path(tmp) / f"{name}.jsonl"
                    path.write_text(line + "\n", encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_jsonl_cases(path)

    def test_jsonl_rejects_duplicate_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicates.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps({"id": "same", "text": "first"}),
                        json.dumps({"id": "same", "text": "second"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate case identifier"):
                load_jsonl_cases(path)

    def test_smoke_suite_covers_all_child_skills(self):
        smoke_path = Path(__file__).resolve().parents[1] / "evals" / "cases" / "smoke.jsonl"
        results = evaluate_suite(smoke_path)
        expected_rubrics = {
            "zero-base-learning",
            "fuzzy-understanding",
            "deepening-learning",
            "problem-solving",
            "mistake-review",
            "study-plan-builder",
            "word",
            "text-memorizer",
        }

        self.assertEqual({result["rubric"] for result in results}, expected_rubrics)
        self.assertEqual(len(results), len(expected_rubrics))
        self.assertTrue(all(result["passed"] for result in results))


if __name__ == "__main__":
    unittest.main()
