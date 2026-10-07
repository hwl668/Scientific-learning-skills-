# -*- coding: utf-8 -*-
"""Dump per-case judging materials for inline provisional judging.

Prints a case's gold metadata, the three condition responses in full, and the
simulated-learner record (if present) so the maintainer can score them against
the frozen JUDGE_SYSTEM_PROMPT_V2 rubric without an API judge. Used for the
pilot20-v2 provisional report; an authorized API judge re-run can reuse this.
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from learning_agent.bench.cases import load_cases  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="pilot20-v2")
    parser.add_argument("--case", required=True, help="case id")
    parser.add_argument("--max-chars", type=int, default=6000, help="truncate each response at this length")
    parser.add_argument("--tail", type=int, default=0, help="also print the last N chars of each response")
    parser.add_argument("--compact", action="store_true", help="skip learner diag replies (post-test only)")
    args = parser.parse_args()

    run_dir = PROJECT_ROOT / "artifacts" / "bench" / args.run_id
    run_config = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in load_cases(Path(run_config["cases_file"]))}
    case = cases[args.case]

    print(f"### CASE {case['id']} | level={case.get('student_level')} | intended={case['intended_skill']}")
    print(f"QUERY: {case['text']}")
    if case.get("gold"):
        print("GOLD: " + json.dumps(case["gold"], ensure_ascii=False))
    if case.get("post_test"):
        print("POST_TEST:")
        for tier, item in case["post_test"].items():
            print(f"  [{tier}] {item['question']}")
            print(f"      REF: {item['reference_answer']}")

    responses = {}
    for line in (run_dir / "responses.jsonl").open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if r["case_id"] == args.case:
            responses[r["condition"]] = r

    for condition in ("base", "generic-tutor", "skills"):
        r = responses.get(condition)
        if not r:
            continue
        text = r["response_text"]
        flag = "TRUNCATED-FOR-DISPLAY" if len(text) > args.max_chars else "full"
        print(f"\n----- RESPONSE [{condition}] ({r['output_tokens']} out-tokens, {flag}) -----")
        print(text[:args.max_chars])
        if args.tail and len(text) > args.max_chars:
            print(f"  …[tail {args.tail}]: {text[-args.tail:]}")

    learner_path = run_dir / "learner.jsonl"
    if learner_path.exists():
        for line in learner_path.open(encoding="utf-8"):
            if not line.strip():
                continue
            lr = json.loads(line)
            if lr["case_id"] == args.case:
                if not args.compact:
                    print(f"\n----- LEARNER [{lr['condition']}] diag-reply -----")
                    print(lr["learner_diag_reply"][:800])
                print("----- LEARNER post-test answers -----")
                for a in (lr.get("answers") or {}).get("answers", []):
                    print(f"  [{a.get('tier')}] {str(a.get('answer'))[:400]}")


if __name__ == "__main__":
    main()
