"""Suite-level metrics for evaluation results."""

from __future__ import annotations


def summarize(results: list[dict]) -> dict:
    judged = [result for result in results if not result.get("is_baseline")]
    baseline = [result for result in results if result.get("is_baseline")]
    if not judged:
        return {
            "total": len(results),
            "judged": 0,
            "baseline": len(baseline),
            "passed": 0,
            "accuracy": 0.0,
            "average_score": 0.0,
            "max_score": 0,
        }
    passed = sum(1 for result in judged if result["passed"])
    max_score = judged[0]["max"]
    return {
        "total": len(results),
        "judged": len(judged),
        "baseline": len(baseline),
        "passed": passed,
        "accuracy": passed / len(judged),
        "average_score": sum(result["total"] for result in judged) / len(judged),
        "max_score": max_score,
    }


def rubric_breakdown(results: list[dict]) -> dict:
    breakdown: dict[str, dict] = {}
    for result in results:
        rubric = result.get("rubric", "concept")
        entry = breakdown.setdefault(rubric, {"count": 0, "passed": 0, "average_score": 0.0})
        entry["count"] += 1
        entry["passed"] += int(result.get("passed", False))
        entry["average_score"] += result.get("total", 0)
    for entry in breakdown.values():
        if entry["count"]:
            entry["average_score"] = entry["average_score"] / entry["count"]
    return breakdown
