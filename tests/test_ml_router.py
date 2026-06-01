import tempfile
import unittest
from pathlib import Path

from learning_agent.ml_router import DEFAULT_DATASET, evaluate_model, load_dataset, predict, route, train_model


class MLRouterTest(unittest.TestCase):
    def test_dataset_loads(self):
        dataset = load_dataset(DEFAULT_DATASET)
        self.assertGreaterEqual(len(dataset.records), 1500)
        self.assertEqual(len(dataset.texts), len(dataset.labels))

    def test_train_and_predict_smoke(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "router.pkl"
            report = Path(tmpdir) / "report.json"
            result = train_model(
                dataset_path=DEFAULT_DATASET,
                artifact_path=artifact,
                report_path=report,
                seed=7,
                test_size=0.2,
            )
            self.assertTrue(artifact.exists())
            self.assertTrue(report.exists())
            self.assertGreaterEqual(result["metrics"]["accuracy"], 0.9)

            fuzzy = predict("我会算矩阵乘法，但不知道它到底表示什么", artifact)
            self.assertEqual(fuzzy["label"], "fuzzy-understanding")
            self.assertIn("top_k", fuzzy)

            non_learning = predict("你是什么 LLM？", artifact)
            self.assertEqual(non_learning["label"], "non-learning")

            routed = route("一个不太像训练集的边界问题", artifact, min_confidence=0.99)
            self.assertTrue(routed["needs_fallback"])

            eval_report = evaluate_model(DEFAULT_DATASET, artifact, seed=7, test_size=0.2)
            self.assertGreaterEqual(eval_report["metrics"]["macro_f1"], 0.9)


if __name__ == "__main__":
    unittest.main()
