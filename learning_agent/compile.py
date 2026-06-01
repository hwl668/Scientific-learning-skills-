#!/usr/bin/env python3
"""Prompt Compiler for Scientific Learning Skills.

Builds platform-specific system prompts from RULES.md, selected skills, and
memory strategy notes while respecting a token budget estimate.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = PROJECT_ROOT / "RULES.md"
SKILLS_DIR = PROJECT_ROOT / "skills"
MEMORY_RULES_PATH = PROJECT_ROOT / "memory" / "review-engine.md"

SUPPORTED_TARGETS = ("claude-code", "codex", "openai", "cursor", "chatgpt", "gpts", "openclaw", "generic")

SKILL_ALIASES = {
    "router": "scientific-learning",
    "scientific": "scientific-learning",
    "zero": "zero-base-learning",
    "zero-base": "zero-base-learning",
    "fuzzy": "fuzzy-understanding",
    "deep": "deepening-learning",
    "problem": "problem-solving",
    "solve": "problem-solving",
    "mistake": "mistake-review",
    "word": "word-deep-dive",
    "text": "text-memorizer",
    "plan": "study-plan-builder",
}

DEFAULT_SKILLS = ("scientific-learning",)


@dataclass(frozen=True)
class CompileResult:
    target: str
    skills: tuple[str, ...]
    estimated_tokens: int
    prompt: str
    truncated: bool = False

    def metadata(self) -> dict:
        return {
            "target": self.target,
            "skills": list(self.skills),
            "estimated_tokens": self.estimated_tokens,
            "truncated": self.truncated,
        }


def estimate_tokens(text: str) -> int:
    """Cheap token estimate good enough for prompt budgeting."""

    ascii_chars = sum(1 for ch in text if ord(ch) < 128)
    non_ascii_chars = len(text) - ascii_chars
    return max(1, int(ascii_chars / 4 + non_ascii_chars / 1.7))


def available_skills() -> list[str]:
    return sorted(path.parent.name for path in SKILLS_DIR.glob("*/SKILL.md"))


def normalize_target(target: str) -> str:
    normalized = target.strip().lower()
    if normalized == "openai-api":
        normalized = "openai"
    if normalized not in SUPPORTED_TARGETS:
        raise ValueError(f"unsupported target {target!r}; choose one of {', '.join(SUPPORTED_TARGETS)}")
    return normalized


def normalize_skill(name: str) -> str:
    raw = name.strip()
    if not raw:
        raise ValueError("empty skill name")
    normalized = SKILL_ALIASES.get(raw, SKILL_ALIASES.get(raw.lower(), raw))
    if normalized not in available_skills():
        raise ValueError(f"unknown skill {name!r}; available: {', '.join(available_skills())}")
    return normalized


def parse_skills(value: str | None) -> tuple[str, ...]:
    if not value or value.strip() in ("", "default"):
        return DEFAULT_SKILLS
    if value.strip() == "all":
        return tuple(available_skills())
    skills = []
    for part in value.split(","):
        skill = normalize_skill(part)
        if skill not in skills:
            skills.append(skill)
    return tuple(skills)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def target_header(target: str) -> str:
    labels = {
        "claude-code": "Claude Code",
        "codex": "OpenAI Codex / API",
        "openai": "OpenAI API",
        "cursor": "Cursor",
        "chatgpt": "ChatGPT / GPTs",
        "gpts": "ChatGPT / GPTs",
        "openclaw": "OpenClaw",
        "generic": "Generic Agent",
    }
    memory_note = "Use local filesystem memory when available." if target in ("claude-code", "cursor", "openclaw", "generic") else "No native filesystem memory; treat memory instructions as behavioral guidance unless external storage is connected."
    return f"""# Compiled Prompt

Target: {labels[target]}

Deployment notes:
- Load this content as the system/developer instruction for the target agent.
- Preserve section boundaries; they help the model locate global rules and skill-specific behavior.
- {memory_note}
"""


def skill_section(skill: str) -> str:
    body = read_text(SKILLS_DIR / skill / "SKILL.md")
    return f"\n\n---\n\n# Skill: {skill}\n\n{body.strip()}\n"


def memory_section() -> str:
    if not MEMORY_RULES_PATH.exists():
        return ""
    return f"\n\n---\n\n# Memory Strategy\n\n{read_text(MEMORY_RULES_PATH).strip()}\n"


def compile_prompt(
    target: str = "generic",
    skills: tuple[str, ...] = DEFAULT_SKILLS,
    token_budget: int | None = None,
    include_memory: bool = True,
) -> CompileResult:
    target = normalize_target(target)
    selected = tuple(normalize_skill(skill) for skill in skills)

    parts = [
        target_header(target),
        "\n\n---\n\n# Global Rules\n\n",
        read_text(RULES_PATH).strip(),
    ]

    for skill in selected:
        parts.append(skill_section(skill))

    if include_memory:
        parts.append(memory_section())

    prompt = "".join(parts).strip() + "\n"
    estimated = estimate_tokens(prompt)
    truncated = False

    if token_budget and estimated > token_budget:
        kept_parts = parts[:3]
        kept_skills = []
        for skill in selected:
            candidate = "".join(kept_parts + [skill_section(skill)] + ([memory_section()] if include_memory else [])).strip() + "\n"
            if estimate_tokens(candidate) <= token_budget:
                kept_parts.append(skill_section(skill))
                kept_skills.append(skill)
            else:
                truncated = True
        if include_memory:
            candidate = "".join(kept_parts + [memory_section()]).strip() + "\n"
            if estimate_tokens(candidate) <= token_budget:
                kept_parts.append(memory_section())
            else:
                truncated = True
        prompt = "".join(kept_parts).strip() + "\n"
        selected = tuple(kept_skills)
        estimated = estimate_tokens(prompt)

    return CompileResult(target=target, skills=selected, estimated_tokens=estimated, prompt=prompt, truncated=truncated)


def deployment_filename(target: str) -> str:
    return {
        "claude-code": "CLAUDE.md",
        "codex": "codex-system-message.md",
        "openai": "openai-system-message.md",
        "cursor": ".cursorrules",
        "chatgpt": "chatgpt-instructions.md",
        "gpts": "gpt-instructions.md",
        "openclaw": "openclaw-rules.md",
        "generic": "agent-system-prompt.md",
    }[target]


def write_output(result: CompileResult, output: Path | None) -> Path | None:
    if output is None:
        print(result.prompt)
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result.prompt, encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile Scientific Learning Skills into a target prompt.")
    parser.add_argument("--target", default="generic", help="target platform")
    parser.add_argument("--skills", default="default", help="comma-separated skills, aliases, default, or all")
    parser.add_argument("--token-budget", type=int, help="estimated token budget")
    parser.add_argument("--output", help="output prompt file")
    parser.add_argument("--no-memory", action="store_true", help="omit memory strategy section")
    parser.add_argument("--metadata", action="store_true", help="print compile metadata as JSON")
    parser.add_argument("--deploy-file", action="store_true", help="write to target-specific default filename under --output dir")
    args = parser.parse_args(argv)

    target = normalize_target(args.target)
    output = Path(args.output) if args.output else None
    if args.deploy_file:
        base = output if output else PROJECT_ROOT / "compiled"
        output = base / deployment_filename(target)

    result = compile_prompt(
        target=target,
        skills=parse_skills(args.skills),
        token_budget=args.token_budget,
        include_memory=not args.no_memory,
    )
    written = write_output(result, output)

    if args.metadata:
        meta = result.metadata()
        if written:
            meta["output"] = str(written)
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
