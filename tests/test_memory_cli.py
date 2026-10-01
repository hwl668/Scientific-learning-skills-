"""Tests for the deterministic memory CLI."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from learning_agent.memory.cli import main
from learning_agent.memory.store import write_json

TODAY = "2026-10-02"
TODAY_DATE = date.fromisoformat(TODAY)


class MemoryCliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.memory_root = Path(self._tmp.name) / "memory"

    def run_cli(self, *argv: str) -> int:
        import contextlib
        import io

        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return main((*argv, "--memory-root", str(self.memory_root)))

    def read_words(self) -> list[dict]:
        data = json.loads(
            (self.memory_root / "word-deep-dive" / "words.json").read_text(encoding="utf-8")
        )
        self.assertIsInstance(data, dict)
        self.assertIsInstance(data["words"], list)
        return data["words"]

    def read_questions(self) -> list[dict]:
        data = json.loads(
            (self.memory_root / "text-memorizer" / "questions.json").read_text(encoding="utf-8")
        )
        self.assertIsInstance(data, list)
        return data

    def test_add_word_creates_defaults(self) -> None:
        code = self.run_cli(
            "add", "--skill", "word-deep-dive",
            "--id", "complimentary", "--word", "complimentary",
            "--exam", "六级", "--note", "免费的；赞美的",
            "--today", TODAY,
        )
        self.assertEqual(code, 0)
        words = self.read_words()
        self.assertEqual(len(words), 1)
        item = words[0]
        self.assertEqual(item["id"], "complimentary")
        self.assertEqual(item["word"], "complimentary")
        self.assertEqual(item["exam"], "六级")
        self.assertEqual(item["created_at"], TODAY)
        self.assertEqual(item["review_count"], 0)
        self.assertEqual(item["correct_streak"], 0)
        self.assertEqual(item["interval_days"], 1)
        self.assertIsNone(item["next_review"])
        self.assertFalse(item["mastered"])

    def test_add_text_question_defaults_to_questions_file(self) -> None:
        code = self.run_cli(
            "add", "--skill", "text-memorizer",
            "--id", "kp-1", "--content", "实践是检验真理的唯一标准",
            "--module", "真理观", "--today", TODAY,
        )
        self.assertEqual(code, 0)
        questions = self.read_questions()
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["module"], "真理观")
        self.assertFalse(
            (self.memory_root / "text-memorizer" / "weak_points.json").exists()
        )

    def test_add_is_idempotent_and_preserves_review_state(self) -> None:
        self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "w1", "--word", "undermine",
            "--today", TODAY,
        )
        self.run_cli(
            "grade", "--skill", "word-deep-dive", "--id", "w1",
            "--correct", "--today", TODAY,
        )
        code = self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "w1", "--word", "undermine",
            "--exam", "考研", "--today", TODAY,
        )
        self.assertEqual(code, 0)
        words = self.read_words()
        self.assertEqual(len(words), 1)
        item = words[0]
        self.assertEqual(item["exam"], "考研")
        self.assertEqual(item["correct_streak"], 1)
        self.assertEqual(item["review_count"], 1)

    def test_grade_correct_advances_interval_and_wrong_resets(self) -> None:
        self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "w1", "--word", "undermine",
            "--today", TODAY,
        )
        self.assertEqual(
            self.run_cli(
                "grade", "--skill", "word-deep-dive", "--id", "w1",
                "--correct", "--today", TODAY,
            ),
            0,
        )
        item = self.read_words()[0]
        self.assertEqual(item["correct_streak"], 1)
        self.assertEqual(item["interval_days"], 1)
        self.assertEqual(item["next_review"], (TODAY_DATE + timedelta(days=1)).isoformat())

        later = "2026-10-03"
        self.assertEqual(
            self.run_cli(
                "grade", "--skill", "word-deep-dive", "--id", "w1",
                "--wrong", "--today", later,
            ),
            0,
        )
        item = self.read_words()[0]
        self.assertEqual(item["correct_streak"], 0)
        self.assertEqual(item["interval_days"], 1)
        self.assertEqual(item["next_review"], "2026-10-04")

    def test_grade_quality_alias_and_mastery(self) -> None:
        self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "w1", "--word", "undermine",
            "--today", TODAY,
        )
        for offset in range(5):
            day = (TODAY_DATE + timedelta(days=offset)).isoformat()
            self.assertEqual(
                self.run_cli(
                    "grade", "--skill", "word-deep-dive", "--id", "w1",
                    "--quality", "5", "--today", day,
                ),
                0,
            )
        item = self.read_words()[0]
        self.assertTrue(item["mastered"])
        self.assertGreaterEqual(item["interval_days"], 16)

    def test_grade_unknown_id_fails_without_writing(self) -> None:
        self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "w1", "--word", "undermine",
            "--today", TODAY,
        )
        before = (self.memory_root / "word-deep-dive" / "words.json").read_text(encoding="utf-8")
        code = self.run_cli(
            "grade", "--skill", "word-deep-dive", "--id", "missing",
            "--correct", "--today", TODAY,
        )
        self.assertEqual(code, 1)
        after = (self.memory_root / "word-deep-dive" / "words.json").read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_due_includes_item_scheduled_for_today(self) -> None:
        # review-engine.md: next_review <= 今天 即到期；答错重置后次日必须被抽到。
        self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "w1", "--word", "undermine",
            "--today", TODAY,
        )
        self.run_cli(
            "grade", "--skill", "word-deep-dive", "--id", "w1",
            "--wrong", "--today", TODAY,
        )
        report = json.loads(self.json_cli(
            "due", "--skill", "word-deep-dive", "--today", "2026-10-03"
        ))
        self.assertEqual([item["id"] for item in report["items"]], ["w1"])
        status = json.loads(self.json_cli(
            "status", "--skill", "word-deep-dive", "--today", "2026-10-03"
        ))
        self.assertEqual(status["due"], 1)

    def test_due_excludes_future_and_never_drops_new_items(self) -> None:
        self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "new1", "--word", "aa",
            "--today", TODAY,
        )
        self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "future1", "--word", "bb",
            "--today", TODAY,
        )
        self.run_cli(
            "grade", "--skill", "word-deep-dive", "--id", "future1",
            "--correct", "--today", TODAY,
        )
        report = json.loads(self.json_cli(
            "due", "--skill", "word-deep-dive", "--today", TODAY
        ))
        ids = [item["id"] for item in report["items"]]
        self.assertIn("new1", ids)
        self.assertNotIn("future1", ids)

        report_all = json.loads(self.json_cli(
            "due", "--skill", "word-deep-dive", "--all", "--today", TODAY
        ))
        self.assertEqual(report_all["total_due"], 2)

    def test_due_weak_only_and_limit(self) -> None:
        for index in range(4):
            self.run_cli(
                "add", "--skill", "word-deep-dive", "--id", f"w{index}", "--word", f"word{index}",
                "--today", TODAY,
            )
        for index in (2, 3):
            self.run_cli(
                "grade", "--skill", "word-deep-dive", "--id", f"w{index}",
                "--correct", "--today", TODAY,
            )
        report = json.loads(self.json_cli(
            "due", "--skill", "word-deep-dive", "--weak-only", "--today", TODAY
        ))
        self.assertEqual(sorted(item["id"] for item in report["items"]), ["w0", "w1"])

        limited = json.loads(self.json_cli(
            "due", "--skill", "word-deep-dive", "--limit", "2", "--today", TODAY
        ))
        # w2/w3 刚复习过，next_review 在明天，未到期；到期只有 w0/w1。
        self.assertEqual(limited["count"], 2)
        self.assertEqual(limited["total_due"], 2)

    def test_status_counts(self) -> None:
        self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "a", "--word", "aa", "--today", TODAY,
        )
        self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "b", "--word", "bb", "--today", TODAY,
        )
        self.run_cli(
            "grade", "--skill", "word-deep-dive", "--id", "b", "--correct", "--today", TODAY,
        )
        status = json.loads(self.json_cli("status", "--skill", "word-deep-dive", "--today", TODAY))
        self.assertEqual(status["total"], 2)
        self.assertEqual(status["mastered"], 0)
        self.assertEqual(status["new"], 1)
        self.assertEqual(status["due"], 1)
        self.assertEqual(status["weakest_ids"][0], "a")

    def test_corrupted_file_is_reported_not_overwritten(self) -> None:
        path = self.memory_root / "word-deep-dive" / "words.json"
        write_json(path, {"words": []})
        path.write_text('{"words": [broken', encoding="utf-8")
        code = self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "w1", "--word", "undermine",
            "--today", TODAY,
        )
        self.assertEqual(code, 1)
        self.assertEqual(path.read_text(encoding="utf-8"), '{"words": [broken')

    def test_rewrite_keeps_backup(self) -> None:
        self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "w1", "--word", "undermine",
            "--today", TODAY,
        )
        self.run_cli(
            "grade", "--skill", "word-deep-dive", "--id", "w1", "--correct", "--today", TODAY,
        )
        backup = self.memory_root / "word-deep-dive" / "words.json.bak"
        self.assertTrue(backup.is_file())

    def test_remove(self) -> None:
        self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "w1", "--word", "undermine",
            "--today", TODAY,
        )
        self.assertEqual(
            self.run_cli("remove", "--skill", "word-deep-dive", "--id", "w1"),
            0,
        )
        self.assertEqual(self.read_words(), [])
        self.assertEqual(
            self.run_cli("remove", "--skill", "word-deep-dive", "--id", "w1"),
            1,
        )

    def test_invalid_today_fails(self) -> None:
        code = self.run_cli(
            "add", "--skill", "word-deep-dive", "--id", "w1", "--word", "undermine",
            "--today", "2026/10/02",
        )
        self.assertEqual(code, 1)

    def test_invalid_skill_rejected(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(
                "add", "--skill", "fuzzy-understanding", "--id", "x", "--content", "y",
                "--today", TODAY,
            )
        self.assertEqual(ctx.exception.code, 2)  # argparse 用法错误约定

    def json_cli(self, *argv: str) -> str:
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main((*argv, "--json", "--memory-root", str(self.memory_root)))
        self.assertEqual(code, 0)
        return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
