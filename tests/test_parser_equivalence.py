"""Behaviour that must be identical with and without PyYAML.

The fallback parser exists so the tool works with no third-party packages. Any
divergence between the two parsers is a bug, because the same skill would then
be judged differently on two machines. These tests assert equivalence on the
inputs skills actually contain.
"""

from __future__ import annotations

import pytest

from skillvet import frontmatter as fm


@pytest.fixture
def no_yaml(monkeypatch):
    monkeypatch.setattr(fm, "_yaml", None)


def _parse_both(tmp_path, monkeypatch, block: str):
    """Parse the same frontmatter with PyYAML and with the fallback."""
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text(f"---\n{block}\n---\n\nbody\n", encoding="utf-8")

    real = fm.__dict__["_yaml"]
    if real is None:
        pytest.skip("PyYAML is not installed, nothing to compare against")
    with_yaml = fm.load(path).data

    monkeypatch.setattr(fm, "_yaml", None)
    without = fm.load(path).data
    monkeypatch.setattr(fm, "_yaml", real)
    return with_yaml, without


CASES = {
    "plain": "name: demo\ndescription: Use when testing.",
    "quoted": 'name: "demo"\ndescription: "Use when testing."',
    "single_quoted": "name: 'demo'\ndescription: 'Use when testing.'",
    "inline_comment": "name: demo  # note\ndescription: Use when testing.",
    "colon_in_quoted_value": 'name: demo\ndescription: "Use when handling a: b pairs."',
    "hash_in_value": "name: demo\ndescription: Use when writing C# code.",
    "nested_map": "name: demo\ndescription: d\nmetadata:\n  author: me\n  version: '1.0'",
    "block_list": "name: demo\ndescription: d\nallowed-tools:\n  - Bash\n  - Read",
    "null_value": "name: demo\ndescription: d\nempty_key:",
    "mixed_shapes": (
        "name: demo\ndescription: hello\nmetadata:\n  k: v\n"
        "allowed-tools:\n  - Bash\ntail: end"
    ),
    "empty_quoted": 'name: demo\ndescription: ""',
    "boolean": "name: demo\ndescription: d\nflag: true",
    "number_like": "name: demo\ndescription: d\ncount: 3",
    "folded_block": "name: demo\ndescription: >\n  Use when the user\n  asks for this.",
    "literal_block": "name: demo\ndescription: |\n  line one\n  line two",
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_parsers_agree(tmp_path, monkeypatch, case):
    with_yaml, without = _parse_both(tmp_path, monkeypatch, CASES[case])
    assert with_yaml == without, f"parsers disagree on {case}"


def test_folded_block_becomes_one_line(tmp_path, no_yaml):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: demo\ndescription: >\n  Use when the user\n  asks for this.\n---\nbody\n",
        encoding="utf-8",
    )
    parsed = fm.load(path)
    assert parsed.get("description") == "Use when the user asks for this."


def test_literal_block_keeps_newlines(tmp_path, no_yaml):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: demo\ndescription: |\n  line one\n  line two\n---\nbody\n",
        encoding="utf-8",
    )
    parsed = fm.load(path)
    assert parsed.get("description") == "line one\nline two"


def test_list_is_rejected_not_silently_emptied(tmp_path, no_yaml):
    """A list frontmatter must raise, not become an empty dict."""
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text("---\n- a\n- b\n---\nbody\n", encoding="utf-8")
    with pytest.raises(fm.FrontmatterError, match="mapping"):
        fm.load(path)


def test_bare_scalar_line_is_rejected(tmp_path, no_yaml):
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text("---\njust a bare line\n---\nbody\n", encoding="utf-8")
    with pytest.raises(fm.FrontmatterError, match="key: value"):
        fm.load(path)


def test_unquoted_colon_is_rejected_by_both_parsers(tmp_path, monkeypatch):
    """An unquoted 'a: b' inside a value is invalid YAML. Both parsers must say so.

    This matters because a lenient fallback would accept a file that a real
    agent cannot load, which hides the bug from the person who wrote it.
    """
    block = "name: demo\ndescription: Use when handling a: b pairs."
    path = tmp_path / "demo" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(f"---\n{block}\n---\nbody\n", encoding="utf-8")

    real = fm.__dict__["_yaml"]
    if real is not None:
        with pytest.raises(fm.FrontmatterError):
            fm.load(path)

    monkeypatch.setattr(fm, "_yaml", None)
    with pytest.raises(fm.FrontmatterError, match="quote the whole value"):
        fm.load(path)