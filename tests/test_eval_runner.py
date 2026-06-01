import json
import tempfile
import unittest
from pathlib import Path

from learning_agent.eval.runner import evaluate, evaluate_suite, render_markdown_report
from learning_agent.eval.scorers import parse_file_meta


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


if __name__ == "__main__":
    unittest.main()
