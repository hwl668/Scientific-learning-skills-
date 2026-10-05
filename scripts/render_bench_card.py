#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render docs/assets/bench-card.{light,dark}.svg from committed bench results.

Reads the newest evals/bench/results/*.json (written by
`python -m learning_agent.bench.report --copy-to evals/bench/results`) and
draws a static three-condition comparison card. Numbers shown are exactly the
numbers in the committed report — the card is re-rendered by
.github/workflows/bench-card.yml whenever results change, so it can never
drift from the evidence. Deterministic output (no timestamps).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "evals" / "bench" / "results"
OUT_DIR = PROJECT_ROOT / "docs" / "assets"

W, H = 760, 336
MARGIN = 28

CONDITIONS = (
    ("base", "Base", "#8c959f", "#6e7681"),
    ("generic-tutor", "Generic tutor", "#656d76", "#9198a1"),
    ("skills", "Scientific Learning Skills", "#0969da", "#58a6ff"),
)

# (label_zh, label_en, key, kind, note) — kind: dim(1-5) | ter(0-1) | tok(index)
GROUPS = (
    ("变式迁移 Transfer (1–5)", "transfer_quality", "dim", None),
    ("TER 靶向解释率", "ter_mean", "ter", None),
    ("输出 tokens (×base)", "output_tokens_index_vs_base", "tok", None),
)

THEMES = {
    "light": {"bg": "#ffffff", "panel": "#f6f8fa", "border": "#d5d9df", "text": "#1f2328", "dim": "#656d76"},
    "dark": {"bg": "#0d1117", "panel": "#161b22", "border": "#30363d", "text": "#e6edf3", "dim": "#9198a1"},
}


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def load_report() -> dict:
    files = sorted(RESULTS_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"no result JSON files in {RESULTS_DIR}")
    return json.loads(files[-1].read_text(encoding="utf-8"))


def value_or_dash(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def bar_width(value: float | None, kind: str) -> float:
    if value is None:
        return 0.0
    if kind == "dim":
        return max(0.0, min(1.0, value / 5.0))
    if kind == "ter":
        return max(0.0, min(1.0, value))
    return max(0.0, min(1.0, value / 1.0))


def render(report: dict, theme: str) -> str:
    c = THEMES[theme]
    conditions = report["conditions"]
    run_id = report["run_id"]
    subject = report.get("subject_model") or "?"
    n_cases = max((agg.get("n_cases") or 0) for agg in conditions.values())
    judge = report.get("judge_model") or "self"

    parts: list[str] = []
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="12" fill="{c["bg"]}" stroke="{c["border"]}"/>')
    parts.append(f'<text x="{MARGIN}" y="34" font-size="15" font-weight="700" fill="{c["text"]}">LearningSkillBench · {esc(run_id)}</text>')
    parts.append(
        f'<text x="{MARGIN}" y="53" font-size="10.5" fill="{c["dim"]}">'
        f"真实模型三条件对照 · {n_cases} cases · subject={esc(subject)} · judge={esc(judge)} (self)</text>"
    )

    y = 74
    bar_x = 240
    bar_max = 330
    for label_zh, key, kind, _note in GROUPS:
        parts.append(f'<text x="{MARGIN}" y="{y + 10}" font-size="11" font-weight="700" fill="{c["text"]}">{esc(label_zh)}</text>')
        row_y = y
        for key_name, label, color_light, color_dark in CONDITIONS:
            color = color_light if theme == "light" else color_dark
            agg = conditions.get(key_name, {})
            if kind == "dim":
                value = (agg.get("dimension_means") or {}).get(key)
            else:
                value = agg.get(key)
            parts.append(f'<text x="{MARGIN + 6}" y="{row_y + 16}" font-size="9.5" fill="{c["dim"]}">{esc(label)}</text>')
            parts.append(f'<rect x="{bar_x}" y="{row_y + 6}" width="{bar_max}" height="12" rx="6" fill="{c["panel"]}" stroke="{c["border"]}"/>')
            width = bar_max * bar_width(value, kind)
            if width > 0:
                parts.append(f'<rect x="{bar_x}" y="{row_y + 6}" width="{width:.1f}" height="12" rx="6" fill="{color}"/>')
            parts.append(
                f'<text x="{bar_x + bar_max + 10}" y="{row_y + 16}" font-size="10.5" '
                f'font-weight="700" fill="{color}">{esc(value_or_dash(value))}</text>'
            )
            row_y += 20
        y = row_y + 12

    footer_y = H - 16
    parts.append(
        f'<text x="{MARGIN}" y="{footer_y}" font-size="9.5" fill="{c["dim"]}">'
        "simulated-learner ≠ 真实学习效果 · LLM-as-judge（自评，天花板压缩区分度） · Level 3 后测三条件 100%（天花板效应）</text>"
    )
    parts.append(
        f'<text x="{MARGIN}" y="{footer_y - 14}" font-size="9.5" fill="{c["dim"]}">'
        "数字只来自 evals/bench/results/ 已提交报告 · 由 bench-card workflow 自动刷新 · 详见该 run 的 report.md</text>"
    )

    font = "-apple-system,'Segoe UI','Noto Sans SC','Microsoft YaHei',sans-serif"
    style = f"text{{font-family:{font}}}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="LearningSkillBench three-condition comparison">\n'
        f"<style>{style}</style>\n" + "\n".join(parts) + "\n</svg>\n"
    )


def main(argv: list[str] | None = None) -> int:
    global RESULTS_DIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--results", type=Path, default=RESULTS_DIR)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    RESULTS_DIR = args.results
    report = load_report()
    args.out.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        out = args.out / f"bench-card.{theme}.svg"
        out.write_text(render(report, theme), encoding="utf-8", newline="\n")
        if not args.quiet:
            print(f"{out.name}: {out.stat().st_size / 1024:.1f} KB (run={report['run_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
