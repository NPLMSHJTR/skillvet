"""Tests for the rule set. Each rule gets a positive and a negative case."""

from __future__ import annotations

DESC = (
    "Extract tables from PDF files and write them to CSV. "
    "Use when the user asks to pull tabular data out of a PDF."
)


def fm(name: str, description: str = DESC, extra: str = "") -> str:
    """Build a frontmatter block with exactly one name key."""
    block = f"name: {name}\ndescription: {description}"
    if extra:
        block += "\n" + extra.strip()
    return block


def test_clean_skill_has_no_findings(make_skill, rules_of):
    skill = make_skill("pdf-tables", fm("pdf-tables"))
    assert rules_of(skill) == set()


def test_missing_name(make_skill, rules_of):
    skill = make_skill("x", f"description: {DESC}")
    assert "SV001" in rules_of(skill)


def test_name_too_long(make_skill, rules_of):
    name = "a" * 65
    skill = make_skill(name, fm(name))
    assert "SV002" in rules_of(skill)


def test_name_with_uppercase(make_skill, rules_of):
    skill = make_skill("PDF-Tables", fm("PDF-Tables"))
    assert "SV003" in rules_of(skill)


def test_name_with_underscore(make_skill, rules_of):
    skill = make_skill("pdf_tables", fm("pdf_tables"))
    assert "SV003" in rules_of(skill)


def test_name_with_double_hyphen(make_skill, rules_of):
    skill = make_skill("pdf--tables", fm("pdf--tables"))
    assert "SV003" in rules_of(skill)


def test_name_with_trailing_hyphen(make_skill, rules_of):
    skill = make_skill("pdf-", fm("pdf-"))
    assert "SV003" in rules_of(skill)


def test_name_with_space(make_skill, rules_of):
    skill = make_skill("pdf tables", fm("pdf tables"))
    assert "SV003" in rules_of(skill)


def test_name_directory_mismatch(make_skill, rules_of):
    skill = make_skill("pdf-tables", fm("other-name"))
    assert "SV006" in rules_of(skill)


def test_missing_description(make_skill, rules_of):
    skill = make_skill("pdf-tables", "name: pdf-tables")
    assert "SV007" in rules_of(skill)


def test_empty_description(make_skill, rules_of):
    skill = make_skill("pdf-tables", 'name: pdf-tables\ndescription: ""')
    assert "SV007" in rules_of(skill)


def test_description_too_long(make_skill, rules_of):
    skill = make_skill(
        "pdf-tables", fm("pdf-tables", "Use when extracting tables. " + ("x" * 1100))
    )
    assert "SV008" in rules_of(skill)


def test_description_without_trigger(make_skill, rules_of):
    skill = make_skill(
        "pdf-tables",
        fm(
            "pdf-tables",
            "Extracts tabular data from PDF documents and writes the result to a "
            "comma separated file for later processing.",
        ),
    )
    assert "SV009" in rules_of(skill)


def test_description_vague_opener(make_skill, rules_of):
    skill = make_skill(
        "pdf-tables",
        fm(
            "pdf-tables",
            "Helps with documents when the user needs some assistance with files "
            "of many kinds.",
        ),
    )
    assert "SV010" in rules_of(skill)


def test_description_too_short(make_skill, rules_of):
    skill = make_skill("pdf-tables", fm("pdf-tables", "Use when PDFs."))
    assert "SV011" in rules_of(skill)


def test_description_with_code_fence(make_skill, rules_of):
    skill = make_skill(
        "pdf-tables",
        'name: pdf-tables\ndescription: "Use when running ```bash ls``` right now"',
    )
    assert "SV007" in rules_of(skill)


def test_compatibility_too_long(make_skill, rules_of):
    skill = make_skill("pdf-tables", fm("pdf-tables", extra=f"compatibility: {'y' * 501}"))
    assert "SV012" in rules_of(skill)


def test_metadata_not_a_mapping(make_skill, rules_of):
    skill = make_skill("pdf-tables", fm("pdf-tables", extra="metadata: just-a-string"))
    assert "SV013" in rules_of(skill)


def test_allowed_tools_not_a_string(make_skill, rules_of):
    skill = make_skill(
        "pdf-tables", fm("pdf-tables", extra="allowed-tools:\n  - Bash\n  - Read")
    )
    assert "SV014" in rules_of(skill)


def test_unknown_key_is_info(make_skill, rules_of):
    skill = make_skill("pdf-tables", fm("pdf-tables", extra="version: 2"))
    assert "SV015" in rules_of(skill)


def test_empty_body(make_skill, rules_of):
    skill = make_skill("pdf-tables", fm("pdf-tables"), body="")
    assert "SV016" in rules_of(skill)


def test_body_too_long(make_skill, rules_of):
    body = "# Title\n\n" + "\n".join(f"step {i}" for i in range(600))
    skill = make_skill("pdf-tables", fm("pdf-tables"), body=body)
    assert "SV017" in rules_of(skill)


def test_body_without_heading(make_skill, rules_of):
    skill = make_skill("pdf-tables", fm("pdf-tables"), body="Just do the thing.\n")
    assert "SV018" in rules_of(skill)


def test_absolute_reference(make_skill, rules_of):
    skill = make_skill(
        "pdf-tables",
        fm("pdf-tables"),
        body="# Title\n\nSee [the guide](/etc/guide.md).\n",
    )
    assert "SV019" in rules_of(skill)


def test_deeply_nested_reference(make_skill, rules_of):
    skill = make_skill(
        "pdf-tables",
        fm("pdf-tables"),
        body="# Title\n\nSee [the guide](references/deep/guide.md).\n",
    )
    assert "SV020" in rules_of(skill)


def test_broken_reference(make_skill, rules_of):
    skill = make_skill(
        "pdf-tables",
        fm("pdf-tables"),
        body="# Title\n\nSee [the guide](references/missing.md).\n",
    )
    assert "SV021" in rules_of(skill)


def test_valid_reference_passes(make_skill, rules_of):
    skill = make_skill(
        "pdf-tables",
        fm("pdf-tables"),
        body="# Title\n\nSee [the guide](references/guide.md).\n",
    )
    (skill.path.parent / "references").mkdir()
    (skill.path.parent / "references" / "guide.md").write_text("x", encoding="utf-8")
    assert "SV021" not in rules_of(skill)


def test_external_link_is_ignored(make_skill, rules_of):
    skill = make_skill(
        "pdf-tables",
        fm("pdf-tables"),
        body="# Title\n\nSee [the docs](https://example.com/a/b/c).\n",
    )
    assert rules_of(skill) == set()


def test_unreferenced_script(make_skill, rules_of):
    skill = make_skill("pdf-tables", fm("pdf-tables"))
    (skill.path.parent / "scripts").mkdir()
    (skill.path.parent / "scripts" / "extract.py").write_text(
        "print(1)\n", encoding="utf-8"
    )
    assert "SV022" in rules_of(skill)


def test_referenced_script_passes(make_skill, rules_of):
    skill = make_skill(
        "pdf-tables",
        fm("pdf-tables"),
        body="# Title\n\nRun `scripts/extract.py` first.\n",
    )
    (skill.path.parent / "scripts").mkdir()
    (skill.path.parent / "scripts" / "extract.py").write_text(
        "print(1)\n", encoding="utf-8"
    )
    assert "SV022" not in rules_of(skill)