"""Tests for the README demo/bench-card SVG assets and their generators.

The committed SVGs must (a) parse, (b) stay inside size budgets, (c) carry the
reduced-motion fallback and locale text, (d) be byte-identical to what the
generators produce from the committed scenario/results (so the card can never
drift from the evidence), and (e) bench-card numbers must match the committed
report JSON.
"""

import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT_ROOT / "docs" / "assets"
SCENARIO = ASSETS / "demo-scenario.json"
RESULTS = PROJECT_ROOT / "evals" / "bench" / "results"

DEMO_BUDGET_BYTES = 45 * 1024
CARD_BUDGET_BYTES = 15 * 1024

LOCALES = ("zh", "en")
THEMES = ("light", "dark")

# Spot-check strings per locale that must appear in the rendered SVG text.
# (The query line is exploded into per-character tspans, so probe the title.)
LOCALE_PROBES = {
    "zh": "同一个问题，两种回答",
    "en": "One question, two tutors",
}


def run_script(script: Path, out_dir: Path) -> None:
    subprocess.run(
        [sys.executable, "-B", str(script), "--out", str(out_dir), "--quiet"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )


class TestScenario(unittest.TestCase):
    def test_scenario_is_valid_and_complete(self):
        scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
        self.assertIn("zh", scenario["locales"])
        self.assertIn("en", scenario["locales"])
        self.assertGreater(scenario["duration_s"], 0)
        for locale, data in scenario["locales"].items():
            with self.subTest(locale=locale):
                for key in ("title", "query", "badge", "phase_labels", "generic_bubbles", "skills_steps"):
                    self.assertIn(key, data)
                self.assertEqual(len(data["generic_bubbles"]), 6)
                self.assertEqual(len(data["skills_steps"]), 5)
                line_limits = {"zh": 24, "en": 46}
                for bubble in data["generic_bubbles"]:
                    self.assertIn(bubble["hit"], (True, False))
                    self.assertLessEqual(max(len(line) for line in bubble["lines"]), line_limits[locale])
                for step in data["skills_steps"]:
                    self.assertIn(step["phase"], scenario["timings_s"]["phase_lit"])
                self.assertEqual(
                    list(data["phase_labels"].keys()), list(scenario["timings_s"]["phase_lit"].keys())
                )


class TestDemoAssets(unittest.TestCase):
    def test_demo_svgs_exist_parse_and_within_budget(self):
        for locale in LOCALES:
            for theme in THEMES:
                path = ASSETS / f"demo-chat.{locale}.{theme}.svg"
                with self.subTest(path=path.name):
                    self.assertTrue(path.exists(), f"{path.name} missing — run scripts/generate_demo_svg.py")
                    self.assertLess(path.stat().st_size, DEMO_BUDGET_BYTES)
                    root = ET.parse(path).getroot()
                    self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
                    style = root.find("{http://www.w3.org/2000/svg}style").text or ""
                    self.assertIn("@keyframes", style)
                    self.assertIn("prefers-reduced-motion", style)

    def test_demo_svgs_carry_locale_text(self):
        for locale, probe in LOCALE_PROBES.items():
            path = ASSETS / f"demo-chat.{locale}.light.svg"
            content = path.read_text(encoding="utf-8")
            self.assertIn(probe, content)
            self.assertNotIn(LOCALE_PROBES["en" if locale == "zh" else "zh"], content)

    def test_demo_svgs_are_theme_specific(self):
        light = (ASSETS / "demo-chat.zh.light.svg").read_text(encoding="utf-8")
        dark = (ASSETS / "demo-chat.zh.dark.svg").read_text(encoding="utf-8")
        self.assertIn("#ffffff", light)
        self.assertIn("#0d1117", dark)

    def test_generator_output_is_deterministic_and_matches_committed(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_script(PROJECT_ROOT / "scripts" / "generate_demo_svg.py", Path(tmp))
            for locale in LOCALES:
                for theme in THEMES:
                    name = f"demo-chat.{locale}.{theme}.svg"
                    committed = (ASSETS / name).read_bytes()
                    fresh = (Path(tmp) / name).read_bytes()
                    self.assertEqual(committed, fresh, f"{name} is stale; re-run scripts/generate_demo_svg.py")


class TestBenchCard(unittest.TestCase):
    def test_bench_cards_exist_parse_and_within_budget(self):
        for theme in THEMES:
            path = ASSETS / f"bench-card.{theme}.svg"
            with self.subTest(path=path.name):
                self.assertTrue(path.exists(), f"{path.name} missing — run scripts/render_bench_card.py")
                self.assertLess(path.stat().st_size, CARD_BUDGET_BYTES)
                root = ET.parse(path).getroot()
                self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")

    def test_card_numbers_match_committed_report(self):
        reports = sorted(RESULTS.glob("*.json"))
        self.assertTrue(reports, "no committed bench results")
        report = json.loads(reports[-1].read_text(encoding="utf-8"))
        card = (ASSETS / "bench-card.light.svg").read_text(encoding="utf-8")

        self.assertIn(report["run_id"], card)
        transfer = report["conditions"]["skills"]["dimension_means"]["transfer_quality"]
        self.assertIn(f"{transfer:.2f}", card)
        ter = report["conditions"]["skills"]["ter_mean"]
        self.assertIn(f"{ter:.2f}", card)
        tokens = report["conditions"]["skills"]["output_tokens_index_vs_base"]
        self.assertIn(f"{tokens:.2f}", card)

    def test_card_renderer_output_is_deterministic_and_matches_committed(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_script(PROJECT_ROOT / "scripts" / "render_bench_card.py", Path(tmp))
            for theme in THEMES:
                name = f"bench-card.{theme}.svg"
                committed = (ASSETS / name).read_bytes()
                fresh = (Path(tmp) / name).read_bytes()
                self.assertEqual(committed, fresh, f"{name} is stale; re-run scripts/render_bench_card.py")


class TestReadmeEmbeds(unittest.TestCase):
    def test_readmes_reference_demo_and_card_with_picture_element(self):
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        readme_en = (PROJECT_ROOT / "README.en.md").read_text(encoding="utf-8")
        for doc, locale in ((readme, "zh"), (readme_en, "en")):
            with self.subTest(readme=locale):
                self.assertIn(f"demo-chat.{locale}.light.svg", doc)
                self.assertIn(f"demo-chat.{locale}.dark.svg", doc)
                self.assertIn("prefers-color-scheme: dark", doc)
                self.assertIn("bench-card.light.svg", doc)
                self.assertIn("not experimental data" if locale == "en" else "非实验数据", doc)


if __name__ == "__main__":
    unittest.main()
