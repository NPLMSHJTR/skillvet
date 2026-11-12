"""Tests for frontmatter parsing."""

from __future__ import annotations

import pytest

from skillvet.frontmatter import FrontmatterError, load, split_frontmatter


def test_splits_on_delimiters():
    text = "---\nname: a\ndescription: b\n---\n\n# Title\n"
    front, body = split_frontmatter(text)
    assert front == "name: a\ndescription: b"
    assert body.strip() == "# Title"


def test_tolerates_byte_order_mark():
    text = "\ufeff---\nname: a\n---\nbody"
    front, body = split_frontmatter(text)
    assert "name: a" in front
    assert body.strip() == "body"


def test_tolerates_leading_blank_lines():
    text = "\n\n---\nname: a\n---\nbody"
    front, _ = split_frontmatter(text)
    assert "name: a" in front


def test_normalizes_crlf():
    text = "---\r\nname: a\r\n---\r\nbody"
    front, body = split_frontmatter(text)
    assert "name: a" in front
    assert body.strip() == "body"


def test_missing_frontmatter_raises():
    with pytest.raises(FrontmatterError, match="must begin with"):
        split_frontmatter("# Just a heading\n")


def test_unterminated_frontmatter_raises():
    with pytest.raises(FrontmatterError, match="unterminated"):
        split_frontmatter("---\nname: a\n# no closing delimiter\n")


def test_load_parses_quoted_values(tmp_path):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        '---\nname: "demo"\ndescription: "Use when testing."\n---\n\nbody\n',
        encoding="utf-8",
    )
    parsed = load(path)
    assert parsed.get("name") == "demo"
    assert parsed.get("description") == "Use when testing."


def test_load_parses_nested_metadata(tmp_path):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: demo\ndescription: d\nmetadata:\n  author: me\n  version: '1.0'\n---\nbody\n",
        encoding="utf-8",
    )
    parsed = load(path)
    assert parsed.get("metadata") == {"author": "me", "version": "1.0"}


def test_load_rejects_non_mapping(tmp_path):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text("---\n- a\n- b\n---\nbody\n", encoding="utf-8")
    with pytest.raises(FrontmatterError, match="mapping"):
        load(path)


def test_body_line_count(tmp_path):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text("---\nname: d\n---\nline1\nline2\nline3\n", encoding="utf-8")
    parsed = load(path)
    assert parsed.body_line_count >= 3