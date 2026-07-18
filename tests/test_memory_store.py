import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import review
import learning_agent.memory.store as memory_store
from learning_agent.memory.store import MemoryStoreError, read_json, write_json


class MemoryStoreTest(unittest.TestCase):
    def test_missing_file_returns_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.json"
            self.assertEqual(read_json(path, default={"items": []}), {"items": []})

    def test_invalid_json_is_not_silently_treated_as_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            path.write_text('{"items": [', encoding="utf-8")

            with self.assertRaisesRegex(MemoryStoreError, "not valid JSON"):
                read_json(path, default={})

    def test_oversized_memory_file_is_rejected_before_json_parsing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            path.write_text(" " * 33, encoding="utf-8")

            with patch.object(memory_store, "MAX_MEMORY_FILE_BYTES", 32):
                with self.assertRaisesRegex(MemoryStoreError, "exceeds"):
                    read_json(path)

    def test_write_is_valid_and_keeps_previous_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            write_json(path, {"version": 1}, keep_backup=False)
            write_json(path, {"version": 2})

            self.assertEqual(read_json(path), {"version": 2})
            backup = path.with_name("memory.json.bak")
            self.assertEqual(json.loads(backup.read_text(encoding="utf-8")), {"version": 1})

    def test_serialization_failure_does_not_replace_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            write_json(path, {"version": 1}, keep_backup=False)

            with self.assertRaises(MemoryStoreError):
                write_json(path, {"bad": object()})

            self.assertEqual(read_json(path), {"version": 1})
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_review_dashboard_stops_on_corrupt_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_root = Path(tmpdir)
            word_dir = memory_root / "word-deep-dive"
            word_dir.mkdir(parents=True)
            (word_dir / "words.json").write_text('{"words": [', encoding="utf-8")

            original_root = review.MEMORY_ROOT
            review.MEMORY_ROOT = memory_root
            try:
                output = StringIO()
                with redirect_stdout(output):
                    result = review.main()
            finally:
                review.MEMORY_ROOT = original_root

            self.assertEqual(result, 1)
            self.assertIn("避免把损坏数据误判为空并覆盖", output.getvalue())

    def test_review_dashboard_rejects_valid_json_with_invalid_schema(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_root = Path(tmpdir)
            word_dir = memory_root / "word-deep-dive"
            word_dir.mkdir(parents=True)
            (word_dir / "words.json").write_text(
                '{"words": ["not-an-object"]}', encoding="utf-8"
            )

            original_root = review.MEMORY_ROOT
            review.MEMORY_ROOT = memory_root
            try:
                output = StringIO()
                with redirect_stdout(output):
                    result = review.main()
            finally:
                review.MEMORY_ROOT = original_root

            self.assertEqual(result, 1)
            self.assertIn("必须是 JSON 对象", output.getvalue())

    def test_review_dashboard_rejects_type_confused_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_root = Path(tmpdir)
            word_dir = memory_root / "word-deep-dive"
            word_dir.mkdir(parents=True)
            (word_dir / "words.json").write_text(
                '{"words": [{"word": "limit", "correct_streak": "5"}]}',
                encoding="utf-8",
            )

            original_root = review.MEMORY_ROOT
            review.MEMORY_ROOT = memory_root
            try:
                output = StringIO()
                with redirect_stdout(output):
                    result = review.main()
            finally:
                review.MEMORY_ROOT = original_root

            self.assertEqual(result, 1)
            self.assertIn("correct_streak 必须是非负整数", output.getvalue())

    def test_review_dashboard_rejects_extreme_numeric_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_root = Path(tmpdir)
            word_dir = memory_root / "word-deep-dive"
            word_dir.mkdir(parents=True)
            (word_dir / "words.json").write_text(
                json.dumps(
                    {
                        "words": [
                            {
                                "word": "limit",
                                "correct_streak": 10**1000,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            original_root = review.MEMORY_ROOT
            review.MEMORY_ROOT = memory_root
            try:
                output = StringIO()
                with redirect_stdout(output):
                    result = review.main()
            finally:
                review.MEMORY_ROOT = original_root

            self.assertEqual(result, 1)
            self.assertIn("correct_streak 超过上限", output.getvalue())


if __name__ == "__main__":
    unittest.main()
