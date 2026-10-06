"""Tests for the lightweight cross-turn learner state store."""

import json
import tempfile
import unittest
from pathlib import Path

from learning_agent.memory.store import MemoryStoreError, write_json
from learning_agent.memory.learner_state import clear_topic, get_topic, list_topics, record_topic


class TestLearnerState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_record_creates_and_accumulates(self):
        record_topic(self.root, "矩阵乘法", "formula_without_understanding",
                     strategy="基向量类比", today="2026-10-01")
        record_topic(self.root, "矩阵乘法", "formula_without_understanding",
                     strategy="对比数乘", verified=True, today="2026-10-02")
        state = get_topic(self.root, "矩阵乘法")
        gap = state["gaps"]["formula_without_understanding"]
        self.assertEqual(gap["count"], 2)
        self.assertEqual(gap["first_seen"], "2026-10-01")
        self.assertEqual(gap["last_seen"], "2026-10-02")
        self.assertTrue(gap["verified"])
        self.assertEqual(gap["strategies_used"], ["基向量类比", "对比数乘"])

    def test_strategy_and_note_lists_are_capped(self):
        for i in range(15):
            record_topic(self.root, "t", "concept_confusion", strategy=f"s{i}", note=f"n{i}",
                         today=f"2026-01-{i % 28 + 1:02d}")
        state = get_topic(self.root, "t")
        gap = state["gaps"]["concept_confusion"]
        self.assertEqual(len(gap["strategies_used"]), 10)
        self.assertEqual(gap["strategies_used"][-1], "s14")
        self.assertEqual(len(gap["notes"]), 5)

    def test_duplicate_strategy_not_duplicated(self):
        record_topic(self.root, "t", "concept_confusion", strategy="same", today="2026-01-01")
        record_topic(self.root, "t", "concept_confusion", strategy="same", today="2026-01-02")
        self.assertEqual(get_topic(self.root, "t")["gaps"]["concept_confusion"]["strategies_used"], ["same"])

    def test_unknown_gap_rejected(self):
        with self.assertRaises(SystemExit):
            record_topic(self.root, "t", "not_a_gap", today="2026-01-01")

    def test_get_missing_topic_returns_none(self):
        self.assertIsNone(get_topic(self.root, "不存在"))

    def test_list_and_clear(self):
        record_topic(self.root, "a", "concept_confusion", today="2026-01-01")
        record_topic(self.root, "b", "derivation_gap", today="2026-01-02")
        summary = list_topics(self.root)
        self.assertEqual([entry["topic"] for entry in summary], ["a", "b"])
        self.assertEqual(clear_topic(self.root, "a"), 1)
        self.assertEqual(clear_topic(self.root, "a"), 0)
        self.assertEqual(len(list_topics(self.root)), 1)

    def test_corrupt_store_raises_instead_of_resetting(self):
        # Privacy contract: damaged user data must surface, never silently reset.
        path = self.root / "learner-state.json"
        path.write_text("{broken json", encoding="utf-8")
        with self.assertRaises(MemoryStoreError):
            record_topic(self.root, "t", "concept_confusion", today="2026-01-01")

    def test_unexpected_shape_raises(self):
        path = self.root / "learner-state.json"
        write_json(path, {"version": 1, "wrong": {}})
        with self.assertRaises(MemoryStoreError):
            list_topics(self.root)

    def test_on_disk_schema_is_stable(self):
        record_topic(self.root, "主题", "symbol_not_understood", strategy="逐符号翻译",
                     note="∑ 下标读错", today="2026-01-03")
        data = json.loads((self.root / "learner-state.json").read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 1)
        gap = data["topics"]["主题"]["gaps"]["symbol_not_understood"]
        for key in ("count", "first_seen", "last_seen", "strategies_used", "verified", "notes"):
            self.assertIn(key, gap)


if __name__ == "__main__":
    unittest.main()
