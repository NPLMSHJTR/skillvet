"""Tests for the dependency-free path.

PyYAML is optional by design. These tests force the fallback parser even when
PyYAML is installed, so the zero-dependency promise stays true.
"""

from __future__ import annotations

import pytest

from skillvet import frontmatter as fm


@pytest.fixture
def no_yaml(monkeypatch):
    """Temporarily hide PyYAML to exercise the fallback parser."""
    monkeypatch.setattr(fm, "_yaml", None)


def test_fallback_parses_flat_keys(tmp_path, no_yaml):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: demo\ndescription: Use when testing the fallback parser.\n---\n\n# D\n",
        encoding="utf-8",
    )
    parsed = fm.load(path)
    assert parsed.used_fallback_parser
    assert parsed.get("name") == "demo"
    assert parsed.get("description") == "Use when testing the fallback parser."


def test_fallback_parses_nested_metadata(tmp_path, no_yaml):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: demo\ndescription: d\nmetadata:\n  author: me\n---\nbody\n",
        encoding="utf-8",
    )
    parsed = fm.load(path)
    assert parsed.get("metadata") == {"author": "me"}


def test_fallback_strips_quotes(tmp_path, no_yaml):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        '---\nname: "demo"\ndescription: \'Use when quoted.\'\n---\nbody\n',
        encoding="utf-8",
    )
    parsed = fm.load(path)
    assert parsed.get("name") == "demo"
    assert parsed.get("description") == "Use when quoted."


def test_fallback_handles_inline_comment(tmp_path, no_yaml):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: demo  # the name\ndescription: Use when commented.\n---\nbody\n",
        encoding="utf-8",
    )
    parsed = fm.load(path)
    assert parsed.get("name") == "demo"


def test_fallback_keeps_hash_inside_value(tmp_path, no_yaml):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: demo\ndescription: Use when handling C# code.\n---\nbody\n",
        encoding="utf-8",
    )
    parsed = fm.load(path)
    assert parsed.get("description") == "Use when handling C# code."


def test_fallback_bool_coercion(tmp_path, no_yaml):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: demo\ndescription: d\nflag: true\n---\nbody\n", encoding="utf-8"
    )
    parsed = fm.load(path)
    assert parsed.get("flag") is True


def test_fallback_still_validates_end_to_end(tmp_path, no_yaml, capsys):
    """A full CLI run with no PyYAML must produce the same verdict."""
    from skillvet.cli import main

    skill_dir = tmp_path / "pdf_tables"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: pdf_tables\ndescription: Helps with files.\n---\n\n", encoding="utf-8"
    )
    assert main([str(tmp_path), "--no-color", "--format", "json"]) == 1
    out = capsys.readouterr().out
    assert "SV003" in out  # underscore in name
    assert "SV016" in out  # empty body