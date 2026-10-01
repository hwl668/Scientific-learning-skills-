"""Guard the routing contract between router.py, SKILL.md, and RULES.md."""

from __future__ import annotations

import unittest

from learning_agent.validate_routing import collect_issues


class RoutingConsistencyTest(unittest.TestCase):
    def test_router_triggers_are_documented(self) -> None:
        issues = collect_issues()
        self.assertEqual(
            issues,
            [],
            "路由契约出现漂移：请同步 skills/scientific-learning/SKILL.md 路由表、"
            "RULES.md 决策树和 word-deep-dive 考试名单后再改动 router 触发词。\n"
            + "\n".join(issues),
        )


if __name__ == "__main__":
    unittest.main()
