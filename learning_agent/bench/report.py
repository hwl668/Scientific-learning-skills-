#!/usr/bin/env python3
"""Aggregate a judged LearningSkillBench run into report.md / report.json.

Reads artifacts/bench/<run-id>/{run.json,responses.jsonl,judgements.jsonl} and
emits, per condition:

- mean Level-2 dimension scores (1-5)
- TER mean (targeted-explanation ratio) with mean judged unit count
- mean output tokens, indexed against `base` (= 1.00)
- Level-3 post-test accuracy per tier and misconception-correction rate, when
  the run included the simulated-learner stage

The report always carries the honesty banner: subject/judge model identities,
mock-run flag, simulated-learner caveat, and case counts. Mock runs are labeled
"pipeline validation only — not evidence" and their aggregate numbers are
omitted from the markdown table body.

Usage::

    python -m learning_agent.bench.report --run-id pilot20
    python -m learning_agent.bench.report --run-id pilot20 --copy-to evals/bench/results
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from learning_agent.bench.runner import DEFAULT_OUTPUT_ROOT

DIMENSIONS = (
    "correctness",
    "diagnostic_precision",
    "mistake_location",
    "explanation_relevance",
    "no_reveal",
    "cognitive_load",
    "hint_quality",
    "misconception_handling",
    "transfer_quality",
)
POST_TEST_TIERS = ("isomorphic", "near_transfer", "far_transfer")
DIMENSION_LABELS_ZH = {
    "correctness": "Correctness 学科正确性",
    "diagnostic_precision": "Diagnosis 诊断命中 (Mistake ID)",
    "mistake_location": "Mistake location 卡点定位",
    "explanation_relevance": "Relevance 解释靶向",
    "no_reveal": "No-reveal 不剧透",
    "cognitive_load": "Cognitive load 认知负荷",
    "hint_quality": "Hint quality 引导质量",
    "misconception_handling": "Misconceptions 误区处理",
    "transfer_quality": "Transfer 变式迁移",
}
LEVEL_LABELS_ZH = {"low": "初学者 low", "mid": "进阶 mid", "high": "高阶 high"}


def _mean(values: list) -> float | None:
    clean = [v for v in values if isinstance(v, (int, float))]
    return round(statistics.fmean(clean), 2) if clean else None


def aggregate(run_dir: Path) -> dict:
    run_config = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    judgements = [
        json.loads(line)
        for line in (run_dir / "judgements.jsonl").open(encoding="utf-8")
        if line.strip()
    ]
    judgements = [j for j in judgements if "judge_parse_error" not in j and "judge_api_error" not in j]
    if not judgements:
        raise ValueError(f"{run_dir}: no valid judgements to aggregate (run bench.judge first)")

    conditions: dict[str, dict] = {}
    case_levels: dict[str, str | None] = {}
    cases_file = run_config.get("cases_file")
    if cases_file and Path(cases_file).exists():
        from learning_agent.bench.cases import load_cases

        try:
            case_levels = {c["id"]: c.get("student_level") for c in load_cases(Path(cases_file))}
        except Exception:
            case_levels = {}

    def _level_of(record: dict) -> str:
        return case_levels.get(record["case_id"]) or "unlabeled"

    for condition in run_config["conditions"]:
        records = [j for j in judgements if j["condition"] == condition]
        if not records:
            continue
        agg: dict = {
            "n_cases": len(records),
            "dimension_means": {dim: _mean([j.get("scores", {}).get(dim) for j in records]) for dim in DIMENSIONS},
            "ter_mean": _mean([j.get("ter") for j in records]),
            "ter_units_mean": _mean([j.get("n_units") for j in records]),
            "output_tokens_mean": _mean([j.get("subject_output_tokens") for j in records]),
        }
        post = [j for j in records if isinstance(j.get("post_test"), dict)]
        if post:
            agg["post_test_accuracy"] = {
                tier: _mean([p["post_test"].get(tier) for p in post]) for tier in POST_TEST_TIERS
            }
            corrected = [j.get("misconception_corrected") for j in post]
            agg["misconception_correction_rate"] = _mean([1.0 if v is True else 0.0 if v is False else None for v in corrected])

        # Stratified by authored learner level (low/mid/high): a beginner harmed by
        # diagnosis must stay visible instead of dissolving into the average.
        by_level: dict[str, dict] = {}
        for level in ("low", "mid", "high", "unlabeled"):
            level_records = [j for j in records if _level_of(j) == level]
            if not level_records:
                continue
            level_agg: dict = {"n_cases": len(level_records)}
            for dim in ("diagnostic_precision", "no_reveal", "cognitive_load", "explanation_relevance", "transfer_quality"):
                level_agg[dim] = _mean([j.get("scores", {}).get(dim) for j in level_records])
            level_post = [j for j in level_records if isinstance(j.get("post_test"), dict)]
            if level_post:
                level_agg["misconception_correction_rate"] = _mean(
                    [1.0 if j.get("misconception_corrected") is True else 0.0 if j.get("misconception_corrected") is False else None for j in level_post]
                )
                level_agg["post_test_mean"] = _mean(
                    [v for j in level_post for v in (j.get("post_test") or {}).values() if isinstance(v, (int, float))]
                )
            by_level[level] = level_agg
        if any(level != "unlabeled" for level in by_level):
            agg["by_level"] = by_level
        conditions[condition] = agg

    base_tokens = conditions.get("base", {}).get("output_tokens_mean")
    if base_tokens:
        for agg in conditions.values():
            tokens = agg.get("output_tokens_mean")
            agg["output_tokens_index_vs_base"] = round(tokens / base_tokens, 2) if tokens else None

    return {
        "run_id": run_config["run_id"],
        "mock": run_config.get("mock", False),
        "provider": run_config.get("provider"),
        "subject_model": run_config.get("subject_model"),
        "judge_model": run_config.get("judge_model"),
        "prompts": run_config.get("prompts"),
        "cases_file": run_config.get("cases_file"),
        "cases_file_sha256": run_config.get("cases_file_sha256"),
        "git_rev": run_config.get("git_rev"),
        "n_judged": len(judgements),
        "conditions": conditions,
    }


def render_markdown(report: dict) -> str:
    conditions = report["conditions"]
    order = [c for c in ("base", "generic-tutor", "skills") if c in conditions]
    condition_names = {"base": "Base", "generic-tutor": "Generic tutor", "skills": "Scientific Learning Skills"}

    lines = [
        f"# LearningSkillBench — run `{report['run_id']}`",
        "",
        "## 诚实边界（必须随结果一起展示）",
        "",
        f"- Subject model: `{report['subject_model']}`（provider `{report['provider']}`）；"
        f"Judge model: `{report['judge_model'] or '未记录'}`",
        f"- 被评判 case 数：{report['n_judged']}；case 文件：`{report['cases_file']}`"
        f"（sha256 `{report['cases_file_sha256']}`）",
        "- Level 2/TER 为 LLM-as-judge 判分，judge prompt 已冻结并随 run.json 发布；",
        "- 若含 Level 3：模拟学习者结果 ≠ 真实学习效果，标注 `simulated-learner`，不能替代真人实验；",
    ]
    if report.get("mock"):
        lines.append("- **MOCK RUN：流水线验证专用，以下数字不构成任何证据，不得引用。**")
    lines += [
        f"- git rev: `{report.get('git_rev') or 'n/a'}`",
        "",
        "## Level 2 — 回答质量（judge 1–5）与 TER",
        "",
    ]

    if report.get("mock"):
        lines.append("> Mock run：表格省略，避免误引用。查看 report.json 仅供检查流水线结构。\n")
    else:
        header = "| 维度 | " + " | ".join(condition_names[c] for c in order) + " |"
        sep = "|---|" + "---:|" * len(order)
        lines += [header, sep]
        for dim in DIMENSIONS:
            row = [DIMENSION_LABELS_ZH[dim]]
            for condition in order:
                value = conditions[condition]["dimension_means"].get(dim)
                row.append("—" if value is None else f"{value:.2f}")
            lines.append("| " + " | ".join(row) + " |")
        ter_row = ["TER 靶向解释率"]
        units_row = ["TER 平均单元数"]
        tokens_row = ["输出 tokens（base=1.00）"]
        for condition in order:
            agg = conditions[condition]
            ter_row.append("—" if agg.get("ter_mean") is None else f"{agg['ter_mean']:.2f}")
            units_row.append("—" if agg.get("ter_units_mean") is None else f"{agg['ter_units_mean']:.1f}")
            tokens_row.append("—" if agg.get("output_tokens_index_vs_base") is None else f"{agg['output_tokens_index_vs_base']:.2f}")
        lines += [
            "| " + " | ".join(ter_row) + " |",
            "| " + " | ".join(units_row) + " |",
            "| " + " | ".join(tokens_row) + " |",
        ]

        post_rows = []
        for condition in order:
            agg = conditions[condition]
            if "post_test_accuracy" in agg:
                post_rows.append((condition, agg))
        if post_rows:
            # 天花板效应自动披露：三条件后测全满分时 Level 3 无区分度。
            accuracies = [agg["post_test_accuracy"].get(t) for _, agg in post_rows for t in POST_TEST_TIERS]
            if accuracies and all(a == 1.0 for a in accuracies if a is not None):
                lines.append(
                    "\n> ⚠️ **天花板效应**：三条件后测均为满分——模拟学习者（强模型）在当前后测难度上"
                    "已无提升空间，Level 3 正确率不构成条件间差异的证据；仅误解纠正率尚有参考价值，"
                    "且需更大样本。v0.5 应提高后测难度或换用更弱/更真实的模拟学习者。"
                )
            lines += [
                "",
                "## Level 3 — 模拟学习者后测（simulated-learner）",
                "",
                "| 条件 | 同构题 | near-transfer | far-transfer | 误解纠正率 |",
                "|---|---:|---:|---:|---:|",
            ]
            for condition, agg in post_rows:
                acc = agg["post_test_accuracy"]
                cells = ["—" if acc.get(tier) is None else f"{acc[tier]:.0%}" for tier in POST_TEST_TIERS]
                mc = agg.get("misconception_correction_rate")
                lines.append(
                    f"| {condition_names[condition]} | " + " | ".join(cells) + f" | {'—' if mc is None else f'{mc:.0%}'} |"
                )

        # Stratified view: same diagnostic treatment can help advanced and hurt
        # beginners (McMiner: +15.9pp vs −12.2pp); averages must not hide that.
        strat = [(c, conditions[c].get("by_level") or {}) for c in order if conditions[c].get("by_level")]
        if strat:
            lines += [
                "",
                "## 按学习者水平分层（case 标注的 student_level）",
                "",
                "> 平均分会掩盖「同一诊断对初学者有害」的风险，此表必须与总体表一起阅读。",
                "",
                "| 水平 | 条件 | n | Diagnosis | No-reveal | Cog. load | Relevance | Transfer | 后测均分 | 误解纠正 |",
                "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
            for level in ("low", "mid", "high", "unlabeled"):
                for condition, by_level in strat:
                    level_agg = by_level.get(level)
                    if not level_agg:
                        continue
                    cells = [
                        "—" if level_agg.get(k) is None else f"{level_agg[k]:.2f}"
                        for k in ("diagnostic_precision", "no_reveal", "cognitive_load", "explanation_relevance", "transfer_quality")
                    ]
                    pt = "—" if level_agg.get("post_test_mean") is None else f"{level_agg['post_test_mean']:.2f}"
                    mc = "—" if level_agg.get("misconception_correction_rate") is None else f"{level_agg['misconception_correction_rate']:.0%}"
                    lines.append(
                        f"| {LEVEL_LABELS_ZH.get(level, level)} | {condition_names[condition]} | {level_agg['n_cases']} | "
                        + " | ".join(cells) + f" | {pt} | {mc} |"
                    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate a judged bench run into a report.")
    parser.add_argument("--run-id", help="run directory name under artifacts/bench/")
    parser.add_argument("--run-dir", type=Path, help="explicit run directory (overrides --run-id, for tests)")
    parser.add_argument("--copy-to", type=Path, help="also copy report.json/report.md into this directory (committed aggregates)")
    args = parser.parse_args(argv)

    if not args.run_dir and not args.run_id:
        parser.error("either --run-id or --run-dir is required")
    run_dir = args.run_dir or (DEFAULT_OUTPUT_ROOT / args.run_id)
    try:
        report = aggregate(run_dir)
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    report_json = run_dir / "report.json"
    report_md = run_dir / "report.md"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"report -> {report_md}\n         {report_json}")

    if args.copy_to:
        args.copy_to.mkdir(parents=True, exist_ok=True)
        (args.copy_to / f"{args.run_id}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (args.copy_to / f"{args.run_id}.md").write_text(render_markdown(report), encoding="utf-8")
        print(f"copied -> {args.copy_to}/{args.run_id}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
