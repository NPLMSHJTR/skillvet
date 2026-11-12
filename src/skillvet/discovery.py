"""Discovery: find skill directories under a set of paths."""

from __future__ import annotations

from pathlib import Path

SKILL_FILENAME = "SKILL.md"

# Directories that never contain skills worth linting, and where a recursive
# walk would otherwise waste time.
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".tox",
}


def find_skill_files(roots: list[Path]) -> list[Path]:
    """Return every SKILL.md at or below the given roots, sorted for stability."""
    found: list[Path] = []

    for root in roots:
        root = root.expanduser()
        if root.is_file() and root.name == SKILL_FILENAME:
            found.append(root)
            continue
        if not root.is_dir():
            continue

        if (root / SKILL_FILENAME).is_file():
            found.append(root / SKILL_FILENAME)

        for candidate in root.rglob(SKILL_FILENAME):
            if candidate in found:
                continue
            if any(part in SKIP_DIRS for part in candidate.parts):
                continue
            found.append(candidate)

    return sorted(found)