"""Check bench cases against the deterministic router to find misroutes.

Kept as a thin wrapper for interactive use; the CI gate is

    python -m learning_agent.bench.validate_cases

which also validates the bench schema (gold/post_test structure, sources).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from learning_agent.bench.validate_cases import main

if __name__ == "__main__":
    raise SystemExit(main(["--min-routing-agreement", "0"]))
