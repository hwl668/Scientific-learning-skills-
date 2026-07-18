#!/usr/bin/env python3
"""Strict, reproducible validation for repository Skill frontmatter."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - depends on caller environment
    raise RuntimeError(
        'PyYAML is required for Skill validation. Install with: pip install -e ".[validation]"'
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILLS_ROOT = PROJECT_ROOT / "skills"
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_FRONTMATTER_CHARS = 16_384
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MISCONCEPTION_HEADER_PATTERN = re.compile(
    r"^\|\s*常见错误\s*\|\s*为什么错\s*\|\s*正确理解\s*\|\s*$",
    re.MULTILINE,
)
MISCONCEPTION_MINIMUM_PATTERN = re.compile(
    r"(?:至少\s*2\s*(?:条|个|行)?|2\s*[-–—至到]\s*3\s*(?:条|个|行)?|2\s*(?:条|个|行))"
)
TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|(?:\s*:?-{3,}:?\s*\|){3}\s*$")


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(loader: UniqueKeyLoader, node: Any, deep: bool = False):
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


@dataclass(frozen=True)
class ValidationResult:
    path: Path
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def _extract_frontmatter(content: str) -> tuple[str, str]:
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("SKILL.md must start with an exact '---' frontmatter delimiter")
    try:
        closing_index = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("SKILL.md is missing the closing '---' frontmatter delimiter") from exc
    frontmatter = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :]).strip()
    if len(frontmatter) > MAX_FRONTMATTER_CHARS:
        raise ValueError(f"frontmatter exceeds {MAX_FRONTMATTER_CHARS} characters")
    if not body:
        raise ValueError("SKILL.md body must not be empty")
    return frontmatter, body


def _has_two_misconception_rows(body: str) -> bool:
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if not MISCONCEPTION_HEADER_PATTERN.fullmatch(line):
            continue
        if index + 1 >= len(lines) or not TABLE_SEPARATOR_PATTERN.fullmatch(lines[index + 1]):
            continue
        rows = 0
        for candidate in lines[index + 2 :]:
            if not candidate.strip().startswith("|"):
                break
            cells = [cell.strip() for cell in candidate.strip().strip("|").split("|")]
            if len(cells) == 3 and all(cells):
                rows += 1
        if rows >= 2:
            return True
    return False


def validate_skill(skill_dir: Path) -> ValidationResult:
    skill_dir = Path(skill_dir)
    skill_file = skill_dir / "SKILL.md"
    errors: list[str] = []
    try:
        content = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return ValidationResult(skill_file, (f"cannot read UTF-8 SKILL.md: {exc}",))

    try:
        frontmatter_text, body = _extract_frontmatter(content)
    except ValueError as exc:
        return ValidationResult(skill_file, (str(exc),))

    try:
        frontmatter = yaml.load(frontmatter_text, Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        return ValidationResult(skill_file, (f"invalid YAML frontmatter: {exc}",))
    if not isinstance(frontmatter, dict):
        return ValidationResult(skill_file, ("frontmatter must be a YAML mapping",))

    unknown = set(frontmatter) - ALLOWED_FRONTMATTER_KEYS
    if unknown:
        errors.append(f"unexpected frontmatter keys: {', '.join(sorted(map(str, unknown)))}")

    name = frontmatter.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("name must be a non-empty string")
    else:
        name = name.strip()
        if len(name) > MAX_NAME_LENGTH:
            errors.append(f"name exceeds {MAX_NAME_LENGTH} characters")
        if not NAME_PATTERN.fullmatch(name):
            errors.append("name must use lowercase hyphen-case")
        if name != skill_dir.name:
            errors.append(f"name {name!r} does not match directory {skill_dir.name!r}")

    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append("description must be a non-empty string")
    else:
        description = description.strip()
        if len(description) > MAX_DESCRIPTION_LENGTH:
            errors.append(f"description exceeds {MAX_DESCRIPTION_LENGTH} characters")
        if "<" in description or ">" in description:
            errors.append("description must not contain angle brackets")

    if "license" in frontmatter and not isinstance(frontmatter["license"], str):
        errors.append("license must be a string")
    if "metadata" in frontmatter and not isinstance(frontmatter["metadata"], dict):
        errors.append("metadata must be a mapping")
    if "allowed-tools" in frontmatter and not isinstance(
        frontmatter["allowed-tools"], (str, list)
    ):
        errors.append("allowed-tools must be a string or list")

    if skill_dir.name != "scientific-learning":
        if "常见误区" not in body:
            errors.append("teaching Skill body is missing the P0 常见误区 section")
        if not MISCONCEPTION_HEADER_PATTERN.search(body):
            errors.append(
                "P0 contract must include the canonical 常见错误/为什么错/正确理解 table header"
            )
        if not (
            MISCONCEPTION_MINIMUM_PATTERN.search(body)
            or _has_two_misconception_rows(body)
        ):
            errors.append("P0 contract must explicitly require at least 2 misconception rows")

    return ValidationResult(skill_file, tuple(errors))


def validate_all(skills_root: Path = DEFAULT_SKILLS_ROOT) -> list[ValidationResult]:
    skills_root = Path(skills_root)
    if not skills_root.is_dir():
        return [ValidationResult(skills_root, ("skills root does not exist",))]
    directories = sorted(path for path in skills_root.iterdir() if path.is_dir())
    if not directories:
        return [ValidationResult(skills_root, ("skills root contains no Skill directories",))]
    return [validate_skill(directory) for directory in directories]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate all repository Skill frontmatter.")
    parser.add_argument("--skills-root", type=Path, default=DEFAULT_SKILLS_ROOT)
    args = parser.parse_args(argv)

    results = validate_all(args.skills_root)
    failures = [result for result in results if not result.valid]
    for result in failures:
        for error in result.errors:
            print(f"ERROR {result.path}: {error}", file=sys.stderr)
    if failures:
        print(f"Skill validation failed: {len(failures)}/{len(results)} invalid", file=sys.stderr)
        return 1
    print(f"Skill validation passed: {len(results)}/{len(results)} valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
