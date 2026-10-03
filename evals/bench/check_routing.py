"""Check bench cases against the deterministic router to find misroutes."""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Scientific-learning-skills")
from learning_agent.router import route

cases_path = Path(r"D:\Scientific-learning-skills\evals\bench\cases.v0.1.jsonl")
cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]

agree = 0
disagreements = []
for case in cases:
    result = route(case["text"])
    if result.skill == case["intended_skill"]:
        agree += 1
    else:
        disagreements.append((case["id"], case["intended_skill"], result.skill, result.matched_rules, case["text"]))

print(f"agreement: {agree}/{len(cases)} = {agree/len(cases):.0%}")
print()
for case_id, expected, actual, rules, text in disagreements:
    print(f"[{case_id}] expected={expected}  got={actual}  rules={','.join(rules)}")
    print(f"    text: {text}")
print()
print(f"total disagreements: {len(disagreements)}")
