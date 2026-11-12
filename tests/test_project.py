"""Tests that lock in the behaviour the README and docs promise.

These are deliberately at the level of "what a user would notice", because the
unit tests in test_rules.py already cover each rule in isolation.
"""

from __future__ import annotations

import json
from pathlib import Path

from skillvet.cli import main

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "examples"


def test_every_shipped_example_passes_strict():
    """The examples must be exemplary. Warnings are errors here."""
    assert EXAMPLES.is_dir(), "examples directory is missing"
    assert main([str(EXAMPLES), "--strict", "--no-color"]) == 0


def test_shipped_examples_are_all_discovered():
    found = sorted(p.parent.name for p in EXAMPLES.glob("*/SKILL.md"))
    assert found == ["changelog-from-tags", "csv-profile", "sql-migration-review"]


def test_docs_reference_every_rule():
    """docs/rules.md must document every rule id that exists in code."""
    from skillvet import rules

    doc = (REPO_ROOT / "docs" / "rules.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    documented = {f"SV{n:03d}" for n in range(1, 100) if f"SV{n:03d}" in doc}
    in_readme = {f"SV{n:03d}" for n in range(1, 100) if f"SV{n:03d}" in readme}

    # Collect the ids the code can actually emit.
    emitted: set[str] = set()
    tmp = REPO_ROOT / "tests" / "_tmp_rule_scan"
    tmp.mkdir(exist_ok=True)
    (tmp / "probe").mkdir(exist_ok=True)
    (tmp / "probe" / "SKILL.md").write_text(
        "---\nname: probe\ndescription: Use when probing every single rule id.\n---\n\n# Probe\n",
        encoding="utf-8",
    )
    from skillvet.frontmatter import load
    from skillvet.rules import Skill, run_all

    path = tmp / "probe" / "SKILL.md"
    skill = Skill(
        path=path,
        directory_name="probe",
        frontmatter=load(path),
        source_text=path.read_text(encoding="utf-8"),
    )
    emitted.update(f.rule for f in run_all(skill))
    for leftover in sorted(tmp.rglob("*"), reverse=True):
        leftover.unlink() if leftover.is_file() else leftover.rmdir()
    tmp.rmdir()

    # Every rule id mentioned anywhere in code must appear in the doc.
    import re

    source = (REPO_ROOT / "src" / "skillvet" / "rules.py").read_text(encoding="utf-8")
    code_ids = set(re.findall(r'"(SV\d{3})"', source))

    missing = code_ids - documented
    assert not missing, f"rules missing from docs/rules.md: {sorted(missing)}"
    assert "SV015" in in_readme, "README rule table should mention SV015"


def test_json_output_is_stable_and_parseable(tmp_path, capsys):
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: demo\n"
        "description: Does a specific thing. Use when the user asks for that thing.\n"
        "---\n\n# Demo\n\nDo it.\n",
        encoding="utf-8",
    )
    main([str(tmp_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert set(payload) == {"skills", "summary"}
    assert set(payload["summary"]) == {"total", "failed", "warnings", "clean", "errors"}
    entry = payload["skills"][0]
    assert set(entry) == {"path", "name", "fatal", "findings"}
    assert payload["summary"]["clean"] == 1
    assert payload["summary"]["errors"] == 0


def test_paths_in_output_are_relative_when_possible(tmp_path, capsys, monkeypatch):
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Use when checking relative paths in output.\n---\n\n# D\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    main([".", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert not Path(payload["skills"][0]["path"]).is_absolute()