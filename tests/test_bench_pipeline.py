"""End-to-end pipeline test: runner -> judge -> report, fully offline via --mock.

Asserts the wiring produces a structurally complete aggregate. Mock scores are
constant by design; this test checks plumbing, not evidence.
"""

import json
import tempfile
import unittest
from pathlib import Path

from learning_agent.bench.judge import main as judge_main
from learning_agent.bench.report import aggregate
from learning_agent.bench.runner import main as runner_main

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEV_CASES = PROJECT_ROOT / "evals" / "bench" / "dev.synthetic.jsonl"


class TestBenchPipeline(unittest.TestCase):
    def run_pipeline(self, with_learner: bool) -> dict:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out_root = Path(tmp.name)
        ids = "zb-001,fz-001,mr-001"

        runner_args = [
            "--cases", str(DEV_CASES), "--ids", ids, "--run-id", "t",
            "--out-root", str(out_root), "--mock",
        ]
        if with_learner:
            runner_args.append("--with-learner")
        self.assertEqual(runner_main(runner_args), 0)

        self.assertEqual(
            judge_main(["--run-dir", str(out_root / "t"), "--mock"]),
            0,
        )

        run_dir = out_root / "t"
        for name in ("run.json", "responses.jsonl", "judgements.jsonl"):
            self.assertTrue((run_dir / name).exists(), name)
        if with_learner:
            self.assertTrue((run_dir / "learner.jsonl").exists(), "learner.jsonl")

        report = aggregate(run_dir)
        self.assertTrue(report["mock"])  # mock runs must be flagged
        self.assertEqual(set(report["conditions"]), {"base", "generic-tutor", "skills"})
        for condition, agg in report["conditions"].items():
            self.assertEqual(agg["n_cases"], 3)
            self.assertEqual(agg["dimension_means"]["correctness"], 4.0)
            self.assertEqual(agg["ter_mean"], 0.67)
            self.assertEqual(agg["output_tokens_index_vs_base"], 1.0)
        if with_learner:
            for agg in report["conditions"].values():
                self.assertEqual(agg["post_test_accuracy"]["isomorphic"], 1.0)
                self.assertEqual(agg["misconception_correction_rate"], 1.0)
        else:
            for agg in report["conditions"].values():
                self.assertNotIn("post_test_accuracy", agg)
        return report

    def test_pipeline_level2(self):
        self.run_pipeline(with_learner=False)

    def test_pipeline_with_simulated_learner(self):
        self.run_pipeline(with_learner=True)

    def test_responses_record_routed_skill(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out_root = Path(tmp.name)
        self.assertEqual(
            runner_main(["--cases", str(DEV_CASES), "--ids", "fz-001", "--run-id", "t",
                         "--out-root", str(out_root), "--mock"]),
            0,
        )
        records = [
            json.loads(line)
            for line in (out_root / "t" / "responses.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        skills_record = next(r for r in records if r["condition"] == "skills")
        self.assertEqual(skills_record["routed_skill"], "fuzzy-understanding")


if __name__ == "__main__":
    unittest.main()
