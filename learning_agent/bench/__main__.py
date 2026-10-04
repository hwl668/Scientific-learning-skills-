"""Thin wrappers so each bench module is directly runnable:

    python -m learning_agent.bench validate|run|judge|report ...
"""

from __future__ import annotations

import sys

from learning_agent.bench import judge, report, runner, validate_cases


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m learning_agent.bench <validate|run|judge|report> [args]", file=sys.stderr)
        return 2
    command, rest = argv[0], argv[1:]
    if command == "validate":
        return validate_cases.main(rest)
    if command == "run":
        return runner.main(rest)
    if command == "judge":
        return judge.main(rest)
    if command == "report":
        return report.main(rest)
    print(f"unknown command {command!r}; expected validate|run|judge|report", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
