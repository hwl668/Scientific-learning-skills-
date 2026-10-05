#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the animated README demo SVG (see docs/assets/demo-scenario.json).

Pure stdlib, deterministic output (no timestamps). Emits one SVG per
(locale, theme) pair into docs/assets/:

    demo-chat.zh.light.svg  demo-chat.zh.dark.svg
    demo-chat.en.light.svg  demo-chat.en.dark.svg

Animation is pure CSS keyframes on a 16s infinite loop (hard cut at the
loop point). Base element opacity is the FINAL frame, so
`prefers-reduced-motion: reduce` (which disables animation) renders the
settled storyboard as a static image. The storyboard is a repo-authored
behavior illustration, not model output or experimental data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = PROJECT_ROOT / "docs" / "assets" / "demo-scenario.json"
OUT_DIR = PROJECT_ROOT / "docs" / "assets"

W, H = 760, 572
MARGIN = 28
COL_W = 346
COL_Y, COL_H = 130, 318
BUBBLE_X, BUBBLE_W, BUBBLE_H, BUBBLE_GAP = 40, 322, 42, 4
STEP_X, STEP_W, STEP_H, STEP_GAP = 398, 322, 50, 4
CHIP_W, CHIP_H = 52, 15
BAR_X_L, BAR_X_R, BAR_W, BAR_H = 28, 386, 300, 10
BAR_RIGHT_SCALE = 0.62  # 0.6× tokens vs 1.0× base

PHASE_ORDER = ("diagnose", "intervene", "verify", "transfer")

THEMES = {
    "light": {
        "bg": "#ffffff", "panel": "#f6f8fa", "card": "#ffffff",
        "border": "#d5d9df", "text": "#1f2328", "dim": "#656d76",
        "accent": "#0969da", "accent_soft": "#ddf4ff",
        "good": "#1a7f37", "miss": "#8c959f",
        "phases": {"diagnose": "#8250df", "intervene": "#0969da", "verify": "#1a7f37", "transfer": "#bf8700"},
    },
    "dark": {
        "bg": "#0d1117", "panel": "#161b22", "card": "#0d1117",
        "border": "#30363d", "text": "#e6edf3", "dim": "#9198a1",
        "accent": "#58a6ff", "accent_soft": "#122d42",
        "good": "#3fb950", "miss": "#6e7681",
        "phases": {"diagnose": "#ab7df8", "intervene": "#58a6ff", "verify": "#3fb950", "transfer": "#d29922"},
    },
}


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fmt_pct(t: float, duration: float) -> str:
    return f"{t / duration * 100:.2f}%"


class Keyframes:
    """Collects named @keyframes rules and element animations."""

    def __init__(self, duration: float):
        self.duration = duration
        self.rules: list[str] = []

    def appear(self, name: str, t_start: float, rise: bool = False, dur: float = 0.45) -> str:
        """Hidden until t_start, visible afterwards (hard loop cut handles reset)."""
        t_in = min(t_start + dur, self.duration - 0.2)
        start = f"{{opacity:0;{('transform:translateY(7px);' if rise else '')}}}"
        end = "{opacity:1;transform:none;}"
        self.rules.append(
            f"@keyframes {name}{{0%,{fmt_pct(t_start, self.duration)}{start}"
            f"{fmt_pct(t_in, self.duration)},100%{end}}}"
        )
        return f"{name} {self.duration:g}s linear infinite both"

    def char_at(self, name: str, t_visible: float) -> str:
        """Typewriter step: character pops in at t_visible (hard on/off)."""
        t_in = min(t_visible + 0.06, self.duration - 0.1)
        self.rules.append(
            f"@keyframes {name}{{0%,{fmt_pct(t_visible, self.duration)}{{opacity:0}}"
            f"{fmt_pct(t_in, self.duration)},100%{{opacity:1}}}}"
        )
        return f"{name} {self.duration:g}s linear infinite both"

    def grow(self, name: str, t_start: float, t_end: float) -> str:
        self.rules.append(
            f"@keyframes {name}{{0%,{fmt_pct(t_start, self.duration)}{{transform:scaleX(0)}}"
            f"{fmt_pct(t_end, self.duration)},100%{{transform:scaleX(1)}}}}"
        )
        return f"{name} {self.duration:g}s linear infinite both"

    def color_at(self, name: str, t_lit: float, base: str, lit: str) -> str:
        """Property stays base until t_lit, then becomes lit (used for fill)."""
        self.rules.append(
            f"@keyframes {name}{{0%,{fmt_pct(t_lit, self.duration)}{{fill:{base}}}"
            f"{fmt_pct(t_lit + 0.3, self.duration)},100%{{fill:{lit}}}}}"
        )
        return f"{name} {self.duration:g}s linear infinite both"


class SVG:
    def __init__(self):
        self.parts: list[str] = []

    def add(self, chunk: str) -> None:
        self.parts.append(chunk)

    def text(
        self,
        x: float,
        y: float,
        content: str,
        size: float,
        fill: str,
        *,
        weight: int | None = None,
        anchor: str = "start",
        cls: str | None = None,
        extra: str = "",
    ) -> None:
        attrs = f'x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"'
        if weight:
            attrs += f' font-weight="{weight}"'
        if cls:
            attrs += f' class="{cls}"'
        if extra:
            attrs += f" {extra}"
        self.add(f'<text {attrs}>{esc(content)}</text>')

    def rect(self, x: float, y: float, w: float, h: float, r: float, fill: str, stroke: str | None = None, extra: str = "") -> None:
        attrs = f'x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"'
        if stroke:
            attrs += f' stroke="{stroke}"'
        if extra:
            attrs += f" {extra}"
        self.add(f"<rect {attrs}/>")


def typewriter_text(svg: SVG, kf: Keyframes, x: float, y: float, content: str, size: float, fill: str, t0: float, t1: float) -> None:
    """Per-character typewriter: char i pops in at its own time slot."""
    step = (t1 - t0) / len(content)
    spans = []
    for i, ch in enumerate(content):
        anim = kf.char_at(f"kq{i}", t0 + i * step)
        spans.append(f'<tspan opacity="1" style="animation:{anim}">{esc(ch)}</tspan>')
    svg.add(
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
        f"xml:space=\"preserve\">{''.join(spans)}</text>"
    )


def render(locale: str, theme: str, scenario: dict) -> str:
    data = scenario["locales"][locale]
    t = scenario["timings_s"]
    duration = scenario["duration_s"]
    c = THEMES[theme]
    kf = Keyframes(duration)
    svg = SVG()

    font = "-apple-system,'Segoe UI','Noto Sans SC','Microsoft YaHei',sans-serif"

    # ---- header -----------------------------------------------------------
    svg.rect(0, 0, W, H, 12, c["bg"], c["border"])
    svg.text(MARGIN, 40, data["title"], 17, c["text"], weight=700)
    svg.text(W - MARGIN, 37, data["corner_tag"], 9.5, c["dim"], anchor="end")

    # ---- user query bubble + typewriter -----------------------------------
    svg.rect(MARGIN, 52, W - 2 * MARGIN, 36, 8, c["accent_soft"], c["accent"])
    svg.add(f'<circle cx="46" cy="70" r="4" fill="{c["accent"]}"/>')
    typewriter_text(svg, kf, 58, 75, data["query"], 13, c["text"], t["query_typewriter_start"], t["query_typewriter_end"])

    # ---- router badge (right side only) -----------------------------------
    bx, bw = W - MARGIN - 272, 272
    badge_anim = kf.appear("kbadge", t["badge"], rise=True)
    svg.add(
        f'<g style="animation:{badge_anim}">'
        f'<rect x="{bx}" y="98" width="{bw}" height="22" rx="11" fill="{c["accent_soft"]}" stroke="{c["accent"]}"/>'
        f'<text x="{bx + bw / 2}" y="113" font-size="10.5" fill="{c["accent"]}" text-anchor="middle">{esc(data["badge"])}</text>'
        f"</g>"
    )

    # ---- columns -----------------------------------------------------------
    svg.rect(MARGIN, COL_Y, COL_W, COL_H, 10, c["panel"], c["border"])
    svg.rect(386, COL_Y, COL_W, COL_H, 10, c["panel"], c["border"])
    svg.add(
        f'<text x="44" y="152" font-size="12.5" font-weight="700" fill="{c["dim"]}">'
        f'{esc(data["left_title"])}<tspan font-weight="400" font-size="10.5"> · {esc(data["left_sub"])}</tspan></text>'
    )
    svg.add(
        f'<text x="402" y="152" font-size="12.5" font-weight="700" fill="{c["accent"]}">'
        f'{esc(data["right_title"])}<tspan font-weight="400" font-size="10.5" fill="{c["dim"]}"> · {esc(data["right_sub"])}</tspan></text>'
    )

    # ---- left: generic tutor bubbles (fast stacking) -----------------------
    for i, bubble in enumerate(data["generic_bubbles"]):
        y = 162 + i * (BUBBLE_H + BUBBLE_GAP)
        anim = kf.appear(f"kg{i}", t["left_bubbles"][i], rise=True)
        mark = ("✓", c["good"]) if bubble["hit"] else ("✕", c["miss"])
        lines = bubble["lines"]
        l1 = f'<text x="52" y="{y + 17}" font-size="10.5" fill="{c["text"]}">{esc(lines[0])}</text>'
        l2 = (
            f'<text x="52" y="{y + 31}" font-size="10.5" fill="{c["dim"]}">{esc(lines[1])}</text>'
            if len(lines) > 1
            else ""
        )
        svg.add(
            f'<g style="animation:{anim}">'
            f'<rect x="{BUBBLE_X}" y="{y}" width="{BUBBLE_W}" height="{BUBBLE_H}" rx="8" fill="{c["card"]}" stroke="{c["border"]}"/>'
            f"{l1}{l2}"
            f'<circle cx="344" cy="{y + 21}" r="8" fill="none" stroke="{mark[1]}"/>'
            f'<text x="344" y="{y + 24.5}" font-size="9.5" fill="{mark[1]}" text-anchor="middle">{mark[0]}</text>'
            f"</g>"
        )

    # ---- right: skills steps (diagnose -> transfer) ------------------------
    phase_colors = c["phases"]
    for i, step in enumerate(data["skills_steps"]):
        y = 162 + i * (STEP_H + STEP_GAP)
        anim = kf.appear(f"ks{i}", t["right_steps"][i], rise=True)
        color = phase_colors[step["phase"]]
        label = data["phase_labels"][step["phase"]]
        lines = step["lines"]
        if len(lines) == 3:
            baselines = [y + 15, y + 28, y + 41]
            size = 10
        else:
            baselines = [y + 20, y + 34]
            size = 10.5
        body = "".join(
            f'<text x="410" y="{b}" font-size="{size}" fill="{c["text"]}">{esc(line)}</text>'
            for line, b in zip(lines, baselines)
        )
        svg.add(
            f'<g style="animation:{anim}">'
            f'<rect x="{STEP_X}" y="{y}" width="{STEP_W}" height="{STEP_H}" rx="8" fill="{c["card"]}" stroke="{c["border"]}"/>'
            f'<rect x="664" y="{y + 8}" width="{CHIP_W}" height="{CHIP_H}" rx="7.5" fill="{color}"/>'
            f'<text x="{664 + CHIP_W / 2}" y="{y + 19}" font-size="9" fill="{c["bg"]}" text-anchor="middle">{esc(label)}</text>'
            f"{body}</g>"
        )

    # ---- footer: methodology phases light up -------------------------------
    xs = [96, 276, 456, 636]
    line_y = 470
    for i, phase in enumerate(PHASE_ORDER):
        x = xs[i]
        lit_t = t["phase_lit"][phase]
        base_fill, lit_fill = c["panel"], phase_colors[phase]
        circle_anim = kf.color_at(f"kp{i}", lit_t, base_fill, lit_fill)
        label_anim = kf.color_at(f"kpl{i}", lit_t, c["dim"], phase_colors[phase])
        label = data["phase_labels"][phase]
        svg.add(f'<circle cx="{x}" cy="{line_y}" r="5.5" fill="{base_fill}" stroke="{phase_colors[phase]}" stroke-width="1.5" style="animation:{circle_anim}"/>')
        svg.text(x + 12, line_y + 4, label, 11, c["dim"], cls=None, extra=f'style="animation:{label_anim}"')
        if i < 3:
            label_w = len(label) * (11 if any("\u4e00" <= ch <= "\u9fff" for ch in label) else 6.4)
            x_start = x + 12 + label_w + 10
            x_end = xs[i + 1] - 14
            svg.add(
                f'<line x1="{x_start}" y1="{line_y}" x2="{x_end}" y2="{line_y}" stroke="{c["border"]}" stroke-width="1.5"/>'
                f'<polygon points="{x_end},{line_y - 3.5} {x_end},{line_y + 3.5} {x_end + 6},{line_y}" fill="{c["border"]}"/>'
            )

    # ---- footer: token bars ------------------------------------------------
    bar_anims = {
        "l": kf.grow("kbgl", *t["left_bar"]),
        "r": kf.grow("kbgr", *t["right_bar"]),
    }
    val_anims = {
        "l": kf.appear("ktl", t["token_values"]),
        "r": kf.appear("ktr", t["token_values"]),
    }
    for side, x, label, value, scale in (
        ("l", BAR_X_L, data["token_label_left"], data["token_value_left"], 1.0),
        ("r", BAR_X_R, data["token_label_right"], data["token_value_right"], BAR_RIGHT_SCALE),
    ):
        svg.text(x, 512, label, 10, c["dim"])
        svg.rect(x, 518, BAR_W, BAR_H, 5, c["card"], c["border"])
        svg.add(
            f'<rect class="bar" x="{x}" y="518" width="{BAR_W * scale}" height="{BAR_H}" rx="5" '
            f'fill="{c["accent"]}" style="transform-box:fill-box;transform-origin:left center;animation:{bar_anims[side]}"/>'
        )
        svg.text(x + BAR_W + 8, 527, value, 10.5, c["dim"], extra=f'style="animation:{val_anims[side]}"')

    svg.text(W / 2, 554, data["tagline"], 11.5, c["dim"], anchor="middle", extra=f'style="animation:{kf.appear("ktag", t["tagline"], rise=True)}"')

    # ---- assemble ----------------------------------------------------------
    reduced = (
        "@media (prefers-reduced-motion:reduce){*{animation-duration:.001s!important;"
        "animation-iteration-count:1!important}}"
    )
    style = (
        f"text{{font-family:{font};-webkit-user-select:none;user-select:none}}"
        f"rect.bar{{transform-box:fill-box;transform-origin:left center}}"
        + "".join(kf.rules)
        + reduced
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="{esc(data["title"])}">\n'
        f"<style>{style}</style>\n{svg.parts[0]}\n" + "\n".join(svg.parts[1:]) + "\n</svg>\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="output directory")
    parser.add_argument("--scenario", type=Path, default=SCENARIO_PATH)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    scenario = json.loads(args.scenario.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)
    for locale in scenario["locales"]:
        for theme in THEMES:
            out = args.out / f"demo-chat.{locale}.{theme}.svg"
            svg = render(locale, theme, scenario)
            out.write_text(svg, encoding="utf-8", newline="\n")
            if not args.quiet:
                print(f"{out.name}: {out.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
