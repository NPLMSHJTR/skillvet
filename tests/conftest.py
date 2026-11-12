"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skillvet.frontmatter import FrontmatterError, load  # noqa: E402
from skillvet.rules import Skill, run_all  # noqa: E402


@pytest.fixture
def make_skill(tmp_path: Path):
    """Create a skill directory on disk and return a parsed Skill."""

    def _make(name: str, frontmatter: str, body: str = "# Title\n\nDo the thing.\n"):
        directory = tmp_path / name
        directory.mkdir(parents=True, exist_ok=True)
        text = f"---\n{frontmatter.strip()}\n---\n\n{body}"
        path = directory / "SKILL.md"
        path.write_text(text, encoding="utf-8")
        parsed = load(path)
        return Skill(
            path=path,
            directory_name=directory.name,
            frontmatter=parsed,
            source_text=text,
        )

    return _make


@pytest.fixture
def rules_of():
    """Run all rules and return a set of rule ids."""

    def _rules_of(skill: Skill) -> set[str]:
        return {finding.rule for finding in run_all(skill)}

    return _rules_of