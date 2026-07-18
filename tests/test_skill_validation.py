import tempfile
import unittest
from pathlib import Path

from learning_agent.validate_skills import validate_all, validate_skill


class SkillValidationTest(unittest.TestCase):
    def _write_skill(
        self,
        root: Path,
        directory: str,
        frontmatter: str,
        body: str | None = None,
    ) -> Path:
        skill_dir = root / directory
        skill_dir.mkdir()
        if body is None:
            body = """# Body

## 常见误区

必须给出至少 2 条真实误区。

| 常见错误 | 为什么错 | 正确理解 |
|---|---|---|
| 错误一 | 原因一 | 理解一 |
| 错误二 | 原因二 | 理解二 |
"""
        (skill_dir / "SKILL.md").write_text(
            f"---\n{frontmatter}\n---\n\n{body}",
            encoding="utf-8",
        )
        return skill_dir

    def test_repository_skills_are_valid(self):
        results = validate_all()
        self.assertTrue(results)
        self.assertTrue(all(result.valid for result in results), results)
        self.assertEqual(len(results), 9)

    def test_invalid_yaml_and_duplicate_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            malformed = self._write_skill(root, "malformed", "name: malformed\ndescription: [")
            duplicate = self._write_skill(
                root,
                "duplicate",
                "name: duplicate\nname: duplicate\ndescription: valid",
            )
            self.assertIn("invalid YAML", validate_skill(malformed).errors[0])
            self.assertIn("duplicate key", validate_skill(duplicate).errors[0])

    def test_empty_description_and_directory_mismatch_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_dir = self._write_skill(
                root,
                "actual-name",
                "name: different-name\ndescription: ''",
            )
            errors = validate_skill(skill_dir).errors
            self.assertTrue(any("does not match directory" in error for error in errors))
            self.assertTrue(any("description must be a non-empty string" in error for error in errors))

    def test_p0_heading_without_table_or_minimum_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_dir = self._write_skill(
                root,
                "weak-contract",
                "name: weak-contract\ndescription: valid",
                body="# Body\n\n## 常见误区\n\n提醒学习者注意。\n",
            )

            errors = validate_skill(skill_dir).errors
            self.assertTrue(any("canonical" in error for error in errors))
            self.assertTrue(any("at least 2" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
