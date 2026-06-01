import unittest
from datetime import date

from learning_agent.memory.scheduler import (
    forgetting_risk,
    mastery_probability,
    review_priority,
    schedule_review,
    sort_for_review,
)


class SchedulerTest(unittest.TestCase):
    def test_successful_reviews_grow_interval(self):
        item = {"id": "limit", "review_count": 0, "correct_streak": 0, "interval_days": 1}
        today = date(2026, 6, 1)

        first = schedule_review(item, quality=5, today=today)
        second = schedule_review(first, quality=5, today=today)
        third = schedule_review(second, quality=5, today=today)

        self.assertEqual(first["interval_days"], 1)
        self.assertEqual(second["interval_days"], 6)
        self.assertGreater(third["interval_days"], second["interval_days"])
        self.assertEqual(third["correct_streak"], 3)
        self.assertGreater(third["ease_factor"], 2.5)

    def test_failed_review_resets_streak_and_interval(self):
        item = {"id": "word", "review_count": 3, "correct_streak": 3, "interval_days": 12, "ease_factor": 2.6}
        updated = schedule_review(item, quality=2, today=date(2026, 6, 1))

        self.assertEqual(updated["correct_streak"], 0)
        self.assertEqual(updated["interval_days"], 1)
        self.assertFalse(updated["mastered"])
        self.assertLess(updated["ease_factor"], 2.6)

    def test_mastery_after_five_correct_reviews(self):
        item = {"id": "concept", "review_count": 4, "correct_streak": 4, "interval_days": 16}
        updated = schedule_review(item, quality=4, today=date(2026, 6, 1))

        self.assertTrue(updated["mastered"])
        self.assertGreaterEqual(updated["correct_streak"], 5)

    def test_priority_prefers_overdue_weak_items(self):
        today = date(2026, 6, 10)
        weak = {"id": "weak", "correct_streak": 0, "review_count": 4, "interval_days": 1, "next_review": "2026-06-01"}
        strong = {"id": "strong", "correct_streak": 4, "review_count": 4, "interval_days": 16, "next_review": "2026-06-20"}

        self.assertGreater(review_priority(weak, today), review_priority(strong, today))
        self.assertGreater(forgetting_risk(weak, today), forgetting_risk(strong, today))
        self.assertLess(mastery_probability(weak, today), mastery_probability(strong, today))

    def test_sort_for_review_uses_priority(self):
        today = date(2026, 6, 10)
        items = [
            {"id": "later", "correct_streak": 2, "interval_days": 4, "next_review": "2026-06-12"},
            {"id": "urgent", "correct_streak": 0, "review_count": 5, "interval_days": 1, "next_review": "2026-06-01"},
        ]

        sorted_items = sort_for_review(items, today)
        self.assertEqual(sorted_items[0]["id"], "urgent")
        self.assertIn("review_priority", sorted_items[0])


if __name__ == "__main__":
    unittest.main()
