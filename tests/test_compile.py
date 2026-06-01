import tempfile
import unittest
from pathlib import Path

from learning_agent.compile import compile_prompt, estimate_tokens, parse_skills


class CompileTest(unittest.TestCase):
    def test_parse_skill_aliases(self):
        self.assertEqual(parse_skills("fuzzy,problem,word"), ("fuzzy-understanding", "problem-solving", "word-deep-dive"))

    def test_compile_prompt_contains_rules_and_skills(self):
        result = compile_prompt(target="codex", skills=parse_skills("router,fuzzy"), include_memory=True)
        self.assertIn("# Global Rules", result.prompt)
        self.assertIn("# Skill: scientific-learning", result.prompt)
        self.assertIn("# Skill: fuzzy-understanding", result.prompt)
        self.assertIn("# Memory Strategy", result.prompt)
        self.assertGreater(result.estimated_tokens, 0)

    def test_token_budget_truncates_skills(self):
        result = compile_prompt(target="generic", skills=parse_skills("all"), token_budget=2500, include_memory=False)
        self.assertLessEqual(result.estimated_tokens, 2500)
        self.assertTrue(result.truncated)

    def test_estimate_tokens_nonempty(self):
        self.assertGreater(estimate_tokens("hello 世界"), 0)


if __name__ == "__main__":
    unittest.main()
