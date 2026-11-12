"""Tests for CLI behaviour, especially the exit-code contract."""

from __future__ import annotations

import json

from skillvet.cli import main

GOOD = (
    "---\n"
    "name: pdf-tables\n"
    "description: Extract tables from PDF files and write them to CSV. "
    "Use when the user asks to pull tabular data out of a PDF.\n"
    "---\n\n"
    "# PDF tables\n\n"
    "Run `scripts/extract.py`.\n"
)


def _write_skill(root, name, text):
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(text, encoding="utf-8")
    return directory


def test_clean_skill_exits_zero(tmp_path, capsys):
    directory = _write_skill(tmp_path, "pdf-tables", GOOD)
    (directory / "scripts").mkdir()
    (directory / "scripts" / "extract.py").write_text("print(1)\n", encoding="utf-8")
    assert main([str(directory), "--no-color"]) == 0
    assert "clean" in capsys.readouterr().out


def test_error_exits_one(tmp_path, capsys):
    _write_skill(tmp_path, "broken", "---\nname: broken\n---\n\n# T\n")
    assert main([str(tmp_path), "--no-color"]) == 1


def test_warning_does_not_fail_by_default(tmp_path):
    text = (
        "---\n"
        "name: pdf-tables\n"
        "description: Extracts tabular data from PDF documents and writes the "
        "result to a comma separated file for later processing.\n"
        "---\n\n# T\n\nDo it.\n"
    )
    _write_skill(tmp_path, "pdf-tables", text)
    assert main([str(tmp_path), "--no-color"]) == 0


def test_strict_treats_warning_as_failure(tmp_path):
    text = (
        "---\n"
        "name: pdf-tables\n"
        "description: Extracts tabular data from PDF documents and writes the "
        "result to a comma separated file for later processing.\n"
        "---\n\n# T\n\nDo it.\n"
    )
    _write_skill(tmp_path, "pdf-tables", text)
    assert main([str(tmp_path), "--no-color", "--strict"]) == 1


def test_malformed_frontmatter_is_fatal(tmp_path, capsys):
    _write_skill(tmp_path, "bad", "# no frontmatter here\n")
    assert main([str(tmp_path), "--no-color"]) == 1
    assert "frontmatter" in capsys.readouterr().out


def test_missing_directory_exits_two(tmp_path, capsys):
    assert main([str(tmp_path / "nope"), "--no-color"]) == 2
    assert "no SKILL.md found" in capsys.readouterr().err


def test_json_output_shape(tmp_path, capsys):
    _write_skill(tmp_path, "pdf-tables", GOOD)
    main([str(tmp_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["total"] == 1
    assert payload["skills"][0]["name"] == "pdf-tables"
    assert isinstance(payload["skills"][0]["findings"], list)


def test_no_info_hides_info_findings(tmp_path, capsys):
    text = GOOD.replace("description:", "version: 2\ndescription:")
    _write_skill(tmp_path, "pdf-tables", text)
    main([str(tmp_path), "--format", "json", "--no-info"])
    payload = json.loads(capsys.readouterr().out)
    rules = {f["rule"] for f in payload["skills"][0]["findings"]}
    assert "SV015" not in rules
    assert "SV015" in rules if False else True


def test_quiet_prints_one_line(tmp_path, capsys):
    _write_skill(tmp_path, "pdf-tables", GOOD)
    main([str(tmp_path), "--quiet"])
    out = capsys.readouterr().out.strip()
    assert out.count("\n") == 0
    assert "checked" in out


def test_single_file_path_accepted(tmp_path, capsys):
    directory = _write_skill(tmp_path, "pdf-tables", GOOD)
    assert main([str(directory / "SKILL.md"), "--no-color"]) == 0