import json
import unittest
from collections import Counter
from learning_agent.ml_router import DEFAULT_DATASET


TRAINING_PATH = DEFAULT_DATASET

EXPECTED_LABELS = {
    "zero-base-learning",
    "fuzzy-understanding",
    "deepening-learning",
    "problem-solving",
    "mistake-review",
    "word-deep-dive",
    "text-memorizer",
    "study-plan-builder",
    "non-learning",
}


class RouterTrainingDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = [
            json.loads(line)
            for line in TRAINING_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_training_file_has_enough_records(self):
        self.assertGreaterEqual(len(self.records), 1500)

    def test_labels_are_expected(self):
        labels = {record["label"] for record in self.records}
        self.assertEqual(labels, EXPECTED_LABELS)

    def test_texts_are_unique(self):
        texts = [record["text"] for record in self.records]
        self.assertEqual(len(texts), len(set(texts)))

    def test_minimum_label_coverage(self):
        counts = Counter(record["label"] for record in self.records)
        for label in EXPECTED_LABELS - {"non-learning"}:
            self.assertGreaterEqual(counts[label], 100, label)
        self.assertGreaterEqual(counts["non-learning"], 30)

    def test_required_fields(self):
        required = {
            "id",
            "text",
            "label",
            "category",
            "subject",
            "topic",
            "source",
            "quality",
            "hard_negative",
            "review_required",
        }
        for record in self.records:
            self.assertTrue(required.issubset(record), record)
            self.assertTrue(record["text"].strip())


if __name__ == "__main__":
    unittest.main()
