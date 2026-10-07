# -*- coding: utf-8 -*-
"""Merge inline-provisional judgements into a run's judgements.jsonl.

Reads a JSON payload (single record or list) and merges per (case_id, condition):
the new record's keys override the existing record's keys, so Level-2 scores and
post-test grading can be written in separate passes without duplication.
"""

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="pilot20-v2")
    parser.add_argument("--payload", required=True, type=Path, help="JSON file: one record or a list")
    args = parser.parse_args()

    run_dir = PROJECT_ROOT / "artifacts" / "bench" / args.run_id
    path = run_dir / "judgements.jsonl"
    existing: dict[tuple[str, str], dict] = {}
    if path.exists():
        for line in path.open(encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                existing[(r["case_id"], r["condition"])] = r

    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = [payload]
    for record in payload:
        key = (record["case_id"], record["condition"])
        merged = {**existing.get(key, {}), **record}
        existing[key] = merged

    ordered = [existing[k] for k in sorted(existing)]
    with path.open("w", encoding="utf-8") as f:
        for r in ordered:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"merged {len(payload)} record(s); file now has {len(ordered)} unique pairs")


if __name__ == "__main__":
    main()
