import json
from pathlib import Path

repo = Path(r"D:\Scientific-learning-skills")
bench = {
    c["id"]: c
    for c in (
        json.loads(line)
        for line in (repo / "evals/bench/cases.v0.1.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
}

CATEGORY = {
    "zero-base-learning": "zero",
    "fuzzy-understanding": "fuzzy",
    "deepening-learning": "deep",
    "problem-solving": "problem",
    "mistake-review": "mistake",
    "word-deep-dive": "word",
    "text-memorizer": "text",
    "study-plan-builder": "plan",
}

# 回归集补充：优先收录曾路由失败的题（修复的守卫），再加覆盖面补充。
picked = [
    "zb-001", "zb-002", "zb-004", "zb-006", "zb-011", "zb-013", "zb-019",
    "fz-001", "fz-004", "fz-006", "fz-007", "fz-011", "fz-014",
    "ps-005", "ps-006", "ps-007", "ps-009", "ps-011", "ps-013", "ps-015", "ps-018", "ps-020",
    "mr-003", "mr-008", "mr-014",
    "dp-005", "dp-010",
    "wd-005",
    "tm-005",
    "sp-005",
]

existing = (repo / "data/routing_cases.jsonl").read_text(encoding="utf-8")
existing_texts = {json.loads(line)["text"] for line in existing.splitlines() if line.strip()}

lines = []
for case_id in picked:
    case = bench[case_id]
    if case["text"] in existing_texts:
        continue
    entry = {"text": case["text"], "skill": case["intended_skill"], "category": CATEGORY[case["intended_skill"]], "from": "bench-v0.1"}
    lines.append(json.dumps(entry, ensure_ascii=False))

with (repo / "data/routing_cases.jsonl").open("a", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"appended {len(lines)} cases")
