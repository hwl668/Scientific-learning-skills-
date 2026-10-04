"""Guard against version drift between the Python package and the Claude plugin."""

import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestVersionConsistency(unittest.TestCase):
    def test_pyproject_and_plugin_versions_match(self):
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        pyproject_version = next(
            line.split("=")[1].strip().strip('"')
            for line in pyproject.splitlines()
            if line.strip().startswith("version")
        )
        plugin = json.loads(
            (PROJECT_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(pyproject_version, plugin["version"])
        self.assertRegex(pyproject_version, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
