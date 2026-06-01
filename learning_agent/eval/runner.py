"""Evaluation runner for demos and JSONL suites."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .metrics import summarize
from .scorers import BASELINE_MARKER, extract_scorable, get_rubric, parse_file_meta


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = PROJECT_ROOT / "demo"

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"


def evaluate(text: str, label: str = "", rubric: str | None = None, is_baseline: bool | None = None) -> dict:
    scorable = extract_scorable(text)
    meta = parse_file_meta(text)
    if rubric:
        meta["rubric"] = rubric
    if is_baseline is not None:
        meta["is_baseline"] = is_baseline

    scorers, max_score, threshold = get_rubric(meta)

    scores = {}
    total = 0
    for name, scorer in scorers:
        score, note = scorer(scorable)
        scores[name] = (score, note)
        total += score

    return {
        "label": label,
        "scores": scores,
        "total": total,
        "max": max_score,
        "passed": total >= threshold,
        "rubric": meta["rubric"],
        "is_baseline": meta["is_baseline"],
    }


def find_demo_files(skill: str | None = None) -> list[Path]:
    if not DEMO_DIR.exists():
        return []
    files = [path for path in DEMO_DIR.glob("*.md") if path.name != "README.md"]
    before_after = DEMO_DIR / "before-after"
    if before_after.exists():
        files.extend(path for path in before_after.glob("*.md") if path.name != "README.md")
    if skill:
        files = [path for path in files if skill.lower() in path.name.lower()]
    return sorted(files)


def is_baseline_file(path: Path) -> bool:
    try:
        return BASELINE_MARKER in path.read_text(encoding="utf-8").split("\n")[:10]
    except Exception:
        return False


def is_skill_demo(path: Path) -> bool:
    return not is_baseline_file(path)


def run_demo_eval(skill: str | None = None, quick: bool = False, include_all: bool = False) -> list[dict]:
    files = find_demo_files(skill)
    if quick:
        files = [path for path in files if is_skill_demo(path)]
    elif not include_all:
        pass
    results = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        results.append(evaluate(text, label=f"demo/{path.relative_to(DEMO_DIR)}"))
    return results


def load_jsonl_cases(path: Path) -> list[dict]:
    cases = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if "text" not in case:
                raise ValueError(f"{path}:{line_no}: case must contain text")
            cases.append(case)
    return cases


def evaluate_suite(path: Path) -> list[dict]:
    results = []
    for case in load_jsonl_cases(path):
        label = case.get("id") or case.get("label") or case.get("name") or "<case>"
        results.append(
            evaluate(
                case["text"],
                label=str(label),
                rubric=case.get("rubric"),
                is_baseline=case.get("baseline"),
            )
        )
    return results


def result_to_jsonable(result: dict) -> dict:
    return {
        "label": result["label"],
        "total": result["total"],
        "max": result["max"],
        "passed": result["passed"],
        "rubric": result["rubric"],
        "is_baseline": result["is_baseline"],
        "scores": {name: score for name, (score, _note) in result["scores"].items()},
        "notes": {name: note for name, (_score, note) in result["scores"].items()},
    }


def render_markdown_report(results: list[dict]) -> str:
    summary = summarize(results)
    lines = [
        "# Eval Report",
        "",
        f"- Total cases: {summary['total']}",
        f"- Judged cases: {summary['judged']}",
        f"- Baseline cases: {summary['baseline']}",
        f"- Passed: {summary['passed']}/{summary['judged']}",
        f"- Average score: {summary['average_score']:.1f}/{summary['max_score']}",
        "",
        "| Case | Rubric | Score | Status |",
        "|---|---|---:|---|",
    ]
    for result in results:
        status = "BASELINE" if result["is_baseline"] else "PASS" if result["passed"] else "FAIL"
        lines.append(f"| {result['label']} | {result['rubric']} | {result['total']}/{result['max']} | {status} |")
    return "\n".join(lines)


def print_result(result: dict, verbose: bool = True) -> None:
    status = f"{DIM}BASELINE{NC}" if result["is_baseline"] else f"{GREEN}PASS{NC}" if result["passed"] else f"{RED}FAIL{NC}"
    bar_width = result["max"] // 2
    filled = int(bar_width * result["total"] / result["max"]) if result["max"] > 0 else 0
    bar = f"{GREEN}{'█' * filled}{DIM}{'░' * (bar_width - filled)}{NC}"
    print(f"\n{BOLD}{result['label']} {DIM}[{result['rubric']}]{NC}")
    print(f"  {bar} {status}  {result['total']}/{result['max']}")
    if verbose:
        for name, (score, note) in result["scores"].items():
            color = GREEN if score == 2 else YELLOW if score == 1 else RED
            print(f"  {name:8s} {color}{score}/2{NC}  {DIM}{note}{NC}")


def print_summary(results: list[dict]) -> None:
    summary = summarize(results)
    if summary["judged"]:
        extra = f"（{summary['baseline']} 个 baseline 仅展示）" if summary["baseline"] else ""
        print(f"\n{BOLD}{'='*50}{NC}")
        print(f"{BOLD}汇总: {summary['passed']}/{summary['judged']} 通过, 平均 {summary['average_score']:.1f}/{summary['max_score']}{extra}{NC}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scientific Learning Skills — eval")
    parser.add_argument("--skill", help="只评测指定 skill 的 demo")
    parser.add_argument("--quick", action="store_true", help="只测核心 skill demo（不含 baseline）")
    parser.add_argument("--all", action="store_true", help="测试所有 demo（含 baseline）")
    parser.add_argument("--input-file", help="评测任意文件")
    parser.add_argument("--input-text", help="评测任意文本")
    parser.add_argument("--suite", help="运行 JSONL eval suite")
    parser.add_argument("--report", choices=("text", "json", "markdown"), default="text", help="报告格式")
    parser.add_argument("--quiet", "-q", action="store_true", help="只显示总分")
    parser.add_argument("--json", action="store_true", help="JSON 输出（兼容旧参数，等同 --report json）")
    args = parser.parse_args(argv)

    report_format = "json" if args.json else args.report

    if args.input_text:
        results = [evaluate(args.input_text, label="<stdin>")]
    elif args.input_file:
        path = Path(args.input_file)
        if not path.exists():
            print(f"{RED}文件不存在: {path}{NC}", file=sys.stderr)
            return 1
        results = [evaluate(path.read_text(encoding="utf-8"), label=path.name)]
    elif args.suite:
        path = Path(args.suite)
        if not path.exists():
            print(f"{RED}suite 不存在: {path}{NC}", file=sys.stderr)
            return 1
        results = evaluate_suite(path)
    else:
        results = run_demo_eval(skill=args.skill, quick=args.quick, include_all=args.all)

    if not results:
        print(f"{YELLOW}未找到 eval 输入。使用 --input-file、--input-text 或 --suite。{NC}")
        return 1

    if report_format == "json":
        print(json.dumps({"summary": summarize(results), "results": [result_to_jsonable(r) for r in results]}, ensure_ascii=False, indent=2))
    elif report_format == "markdown":
        print(render_markdown_report(results))
    else:
        for result in results:
            print_result(result, verbose=not args.quiet)
        print_summary(results)

    judged = [result for result in results if not result["is_baseline"]]
    return 0 if all(result["passed"] for result in judged) else 1


if __name__ == "__main__":
    raise SystemExit(main())
