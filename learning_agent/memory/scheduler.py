#!/usr/bin/env python3
"""SM-2 style memory scheduler.

This module keeps the existing memory item shape compatible while adding
Anki-like scheduling signals: ease factor, interval growth, forgetting risk,
mastery probability, and review priority.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta


DEFAULT_EASE_FACTOR = 2.5
MIN_EASE_FACTOR = 1.3
MASTERED_STREAK = 5


@dataclass(frozen=True)
class MemoryState:
    review_count: int = 0
    correct_streak: int = 0
    interval_days: int = 1
    ease_factor: float = DEFAULT_EASE_FACTOR
    last_reviewed: str | None = None
    next_review: str | None = None
    mastered: bool = False

    @classmethod
    def from_item(cls, item: dict) -> "MemoryState":
        return cls(
            review_count=int(item.get("review_count", 0) or 0),
            correct_streak=int(item.get("correct_streak", 0) or 0),
            interval_days=max(1, int(item.get("interval_days", 1) or 1)),
            ease_factor=max(MIN_EASE_FACTOR, float(item.get("ease_factor", DEFAULT_EASE_FACTOR) or DEFAULT_EASE_FACTOR)),
            last_reviewed=item.get("last_reviewed"),
            next_review=item.get("next_review"),
            mastered=bool(item.get("mastered") or int(item.get("correct_streak", 0) or 0) >= MASTERED_STREAK),
        )


def parse_day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def days_overdue(item: dict, today: date | None = None) -> int:
    today = today or date.today()
    due = parse_day(item.get("next_review"))
    if due is None:
        return 1
    return max(0, (today - due).days)


def forgetting_risk(item: dict, today: date | None = None) -> float:
    """Estimate recall failure risk from delay, streak, and ease factor."""

    today = today or date.today()
    state = MemoryState.from_item(item)
    due = parse_day(state.next_review)

    if state.mastered and due and due > today:
        return 0.05

    overdue = days_overdue(item, today)
    interval = max(1, state.interval_days)
    elapsed_ratio = overdue / interval
    streak_discount = min(0.45, state.correct_streak * 0.08)
    ease_discount = min(0.2, (state.ease_factor - MIN_EASE_FACTOR) * 0.08)

    base = 0.25 if overdue == 0 else 0.45
    risk = base + elapsed_ratio * 0.45 - streak_discount - ease_discount
    return round(min(0.99, max(0.01, risk)), 3)


def mastery_probability(item: dict, today: date | None = None) -> float:
    state = MemoryState.from_item(item)
    if state.mastered:
        return 0.98
    streak_signal = min(0.7, state.correct_streak * 0.14)
    ease_signal = min(0.15, (state.ease_factor - MIN_EASE_FACTOR) * 0.06)
    risk_penalty = forgetting_risk(item, today) * 0.35
    probability = 0.2 + streak_signal + ease_signal - risk_penalty
    return round(min(0.97, max(0.03, probability)), 3)


def review_priority(item: dict, today: date | None = None) -> float:
    """Higher means the item should be reviewed earlier."""

    today = today or date.today()
    state = MemoryState.from_item(item)
    if state.mastered:
        return 0.0
    risk = forgetting_risk(item, today)
    overdue_bonus = min(1.0, days_overdue(item, today) / max(1, state.interval_days))
    weak_bonus = max(0.0, (3 - state.correct_streak) * 0.12)
    repeated_failure_bonus = min(0.25, state.review_count * 0.02 if state.correct_streak == 0 else 0)
    return round(min(1.0, risk + overdue_bonus * 0.25 + weak_bonus + repeated_failure_bonus), 3)


def _updated_ease_factor(ease_factor: float, quality: int) -> float:
    q = max(0, min(5, int(quality)))
    updated = ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    return round(max(MIN_EASE_FACTOR, updated), 3)


def schedule_review(item: dict, quality: int, today: date | None = None, response_seconds: float | None = None) -> dict:
    """Return a new memory item after applying one review result.

    quality follows SM-2 semantics:
    0-2 = failed recall, 3-5 = successful recall with increasing confidence.
    """

    today = today or date.today()
    state = MemoryState.from_item(item)
    q = max(0, min(5, int(quality)))
    correct = q >= 3
    ease = _updated_ease_factor(state.ease_factor, q)

    updated = dict(item)
    updated["review_count"] = state.review_count + 1
    updated["last_reviewed"] = today.isoformat()
    updated["ease_factor"] = ease

    if correct:
        streak = state.correct_streak + 1
        if streak == 1:
            interval = 1
        elif streak == 2:
            interval = 6
        else:
            interval = max(1, int(round(state.interval_days * ease)))
        updated["correct_streak"] = streak
        updated["interval_days"] = interval
        updated["mastered"] = streak >= MASTERED_STREAK
    else:
        updated["correct_streak"] = 0
        updated["interval_days"] = 1
        updated["mastered"] = False

    updated["next_review"] = (today + timedelta(days=int(updated["interval_days"]))).isoformat()

    if response_seconds is not None:
        updated["last_response_seconds"] = max(0.0, float(response_seconds))

    updated["forgetting_risk"] = forgetting_risk(updated, today)
    updated["mastery_probability"] = mastery_probability(updated, today)
    updated["review_priority"] = review_priority(updated, today)
    return updated


def enrich_item(item: dict, today: date | None = None) -> dict:
    enriched = dict(item)
    enriched["forgetting_risk"] = forgetting_risk(enriched, today)
    enriched["mastery_probability"] = mastery_probability(enriched, today)
    enriched["review_priority"] = review_priority(enriched, today)
    if "ease_factor" not in enriched:
        enriched["ease_factor"] = DEFAULT_EASE_FACTOR
    return enriched


def sort_for_review(items: list[dict], today: date | None = None) -> list[dict]:
    today = today or date.today()
    return sorted(
        (enrich_item(item, today) for item in items),
        key=lambda item: (
            -item.get("review_priority", 0),
            item.get("next_review") or "0000-00-00",
            item.get("id") or item.get("word") or item.get("content") or "",
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply SM-2 style scheduling to one memory item JSON.")
    parser.add_argument("item_json", help="memory item as JSON")
    parser.add_argument("--quality", type=int, required=True, help="SM-2 quality score, 0-5")
    parser.add_argument("--today", help="override today's date, YYYY-MM-DD")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args(argv)

    item = json.loads(args.item_json)
    today = parse_day(args.today) if args.today else date.today()
    if today is None:
        parser.error("--today must be YYYY-MM-DD")
    updated = schedule_review(item, quality=args.quality, today=today)

    if args.json:
        print(json.dumps(updated, ensure_ascii=False, indent=2))
    else:
        print(
            f"interval={updated['interval_days']}d "
            f"next={updated['next_review']} "
            f"ease={updated['ease_factor']:.2f} "
            f"mastery={updated['mastery_probability']:.2f} "
            f"risk={updated['forgetting_risk']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
