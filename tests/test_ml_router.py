import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import learning_agent.ml_router as ml_router
from learning_agent.ml_router import (
    ARTIFACT_FORMAT,
    ARTIFACT_SCHEMA_VERSION,
    DEFAULT_ARTIFACT,
    DEFAULT_DATASET,
    DEFAULT_REPORT,
    DEFAULT_TRAIN_ARTIFACT,
    DEFAULT_TRAIN_REPORT,
    MAX_ROUTER_TEXT_CHARS,
    RouterArtifactError,
    RouterBenchmarkError,
    evaluate_model,
    load_dataset,
    load_model,
    predict,
    route,
    train_model,
)


class MLRouterTest(unittest.TestCase):
    def test_dataset_loads(self):
        dataset = load_dataset(DEFAULT_DATASET)
        self.assertGreaterEqual(len(dataset.records), 1500)
        self.assertEqual(len(dataset.texts), len(dataset.labels))

    def test_train_and_predict_smoke(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "router.json.gz"
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
            self.assertEqual(result["artifact"]["format"], ARTIFACT_FORMAT)
            self.assertEqual(result["artifact"]["schema_version"], ARTIFACT_SCHEMA_VERSION)
            self.assertEqual(result["split"]["group_field"], "topic")
            self.assertEqual(result["split"]["effective_group_overlap_count"], 0)
            self.assertIn("non-learning", result["split"]["fallbacks"])
            self.assertEqual(len(result["dataset_sha256"]), 64)
            self.assertIn("scikit-learn", result["training_dependencies"])
            self.assertEqual(len(result["holdout_record_ids"]), result["test_total"])
            self.assertEqual(artifact.read_bytes()[:2], b"\x1f\x8b")

            fuzzy = predict("我会算矩阵乘法，但不知道它到底表示什么", artifact)
            self.assertEqual(fuzzy["label"], "fuzzy-understanding")
            self.assertIn("top_k", fuzzy)

            non_learning = predict("你是什么 LLM？", artifact)
            self.assertEqual(non_learning["label"], "non-learning")

            routed = route(
                "一个不太像训练集的边界问题",
                artifact,
                min_confidence=0.99,
                top_k=1,
            )
            self.assertTrue(routed["needs_fallback"])
            self.assertEqual(len(routed["top_k"]), 1)

            with patch.object(
                ml_router,
                "_split_indices",
                side_effect=AssertionError("stored holdout should be replayed"),
            ):
                eval_report = evaluate_model(DEFAULT_DATASET, DEFAULT_ARTIFACT)
            self.assertGreaterEqual(eval_report["metrics"]["macro_f1"], 0.9)
            self.assertTrue(eval_report["dataset_matches_training"])
            self.assertEqual(eval_report["split"]["group_field"], "topic")
            self.assertTrue(eval_report["split"]["replayed_from_benchmark"])
            self.assertFalse(eval_report["split"]["artifact_holdout_used"])

            second_artifact = Path(tmpdir) / "router-second.json.gz"
            train_model(
                dataset_path=DEFAULT_DATASET,
                artifact_path=second_artifact,
                report_path=Path(tmpdir) / "report-second.json",
                seed=7,
                test_size=0.2,
            )
            self.assertEqual(artifact.read_bytes(), second_artifact.read_bytes())

    def test_checked_in_artifact_loads_without_pickle(self):
        model, metadata = load_model(DEFAULT_ARTIFACT)
        self.assertEqual(metadata["model_type"], "tfidf_char_ngram_logistic_regression")
        self.assertEqual(len(metadata["dataset_sha256"]), 64)
        self.assertIn("fuzzy-understanding", model.classes_)
        result = predict("学过极限但还是不理解为什么", DEFAULT_ARTIFACT)
        self.assertIn(result["label"], model.classes_)

        report = json.loads(DEFAULT_REPORT.read_text(encoding="utf-8"))
        artifact_sha256 = hashlib.sha256(DEFAULT_ARTIFACT.read_bytes()).hexdigest()
        dataset_sha256 = hashlib.sha256(DEFAULT_DATASET.read_bytes()).hexdigest()
        self.assertEqual(artifact_sha256, report["artifact"]["sha256"])
        self.assertEqual(dataset_sha256, report["dataset_sha256"])

    def test_router_rejects_empty_and_oversized_inputs(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            predict("   ", DEFAULT_ARTIFACT)
        with self.assertRaisesRegex(ValueError, "limit"):
            predict("x" * (MAX_ROUTER_TEXT_CHARS + 1), DEFAULT_ARTIFACT)

    def test_schema_rejects_unbounded_ngram_range(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = json.loads(gzip.decompress(DEFAULT_ARTIFACT.read_bytes()))
            payload["vectorizer"]["ngram_range"] = [1, 1_000_000]
            path = Path(tmpdir) / "router.json.gz"
            path.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8")))
            with self.assertRaisesRegex(RouterArtifactError, "must be \[2, 5\]"):
                load_model(path)

    def test_schema_rejects_unknown_labels_and_invalid_metadata_types(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = json.loads(gzip.decompress(DEFAULT_ARTIFACT.read_bytes()))
            payload["classifier"]["classes"][0] = "unexpected-route"
            path = Path(tmpdir) / "unknown-label.json.gz"
            path.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8")))
            with self.assertRaisesRegex(RouterArtifactError, "do not match project router labels"):
                load_model(path)

            payload = json.loads(gzip.decompress(DEFAULT_ARTIFACT.read_bytes()))
            payload["metadata"]["seed"] = "42"
            path = Path(tmpdir) / "invalid-metadata.json.gz"
            path.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8")))
            with self.assertRaisesRegex(RouterArtifactError, "metadata.seed must be an integer"):
                load_model(path)

    def test_artifact_cannot_choose_its_own_evaluation_holdout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = json.loads(gzip.decompress(DEFAULT_ARTIFACT.read_bytes()))
            dataset = load_dataset(DEFAULT_DATASET)
            original = set(payload["metadata"]["holdout_record_ids"])
            alternate_ids = [
                record_id
                for record_id in ml_router._record_keys(dataset)
                if record_id not in original
            ][: payload["metadata"]["test_total"]]
            self.assertEqual(len(alternate_ids), payload["metadata"]["test_total"])
            payload["metadata"]["holdout_record_ids"] = alternate_ids
            path = Path(tmpdir) / "self-selected-holdout.json.gz"
            path.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8")))

            with self.assertRaisesRegex(RouterBenchmarkError, "does not match"):
                evaluate_model(DEFAULT_DATASET, path)

    def test_benchmark_must_match_evaluation_dataset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = json.loads(DEFAULT_REPORT.read_text(encoding="utf-8"))
            report["dataset_sha256"] = "0" * 64
            benchmark = Path(tmpdir) / "wrong-dataset.json"
            benchmark.write_text(json.dumps(report), encoding="utf-8")

            with self.assertRaisesRegex(RouterBenchmarkError, "fingerprint"):
                evaluate_model(DEFAULT_DATASET, DEFAULT_ARTIFACT, benchmark_path=benchmark)

    def test_schema_rejects_excessive_coefficient_matrix_before_conversion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "router.json.gz"
            path.write_bytes(DEFAULT_ARTIFACT.read_bytes())
            with patch.object(ml_router, "MAX_ARTIFACT_COEFFICIENTS", 1):
                with self.assertRaisesRegex(RouterArtifactError, "coefficients; limit"):
                    load_model(path)

    def test_unsafe_legacy_artifacts_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy = Path(tmpdir) / "router.pkl"
            legacy.write_bytes(b"not even a pickle")
            with self.assertRaisesRegex(RouterArtifactError, "refusing unsafe legacy"):
                load_model(legacy)

    def test_training_rejects_output_path_collisions_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collision = Path(tmpdir) / "collision.json.gz"
            original = b"keep-existing-content"
            collision.write_bytes(original)

            with self.assertRaisesRegex(ValueError, "artifact and report paths must be different"):
                train_model(
                    dataset_path=DEFAULT_DATASET,
                    artifact_path=collision,
                    report_path=collision,
                )

            self.assertEqual(collision.read_bytes(), original)

    def test_default_training_outputs_cannot_overwrite_checked_in_benchmark(self):
        self.assertNotEqual(DEFAULT_TRAIN_ARTIFACT.resolve(), DEFAULT_ARTIFACT.resolve())
        self.assertNotEqual(DEFAULT_TRAIN_REPORT.resolve(), DEFAULT_REPORT.resolve())

        with tempfile.TemporaryDirectory() as tmpdir:
            protected_report = Path(tmpdir) / "frozen-report.json"
            protected_report.write_bytes(DEFAULT_REPORT.read_bytes())
            original = protected_report.read_bytes()
            with patch.object(ml_router, "DEFAULT_REPORT", protected_report):
                with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                    train_model(
                        dataset_path=DEFAULT_DATASET,
                        artifact_path=Path(tmpdir) / "candidate.json.gz",
                        report_path=protected_report,
                    )

            self.assertEqual(protected_report.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
