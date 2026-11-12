"""The rule set.

Every rule is a small function that receives a Skill and appends Findings. Rules
are split into three severities:

    error    the skill violates the Agent Skills specification, or will not load
    warning  the skill will load but is likely to under-trigger or misbehave
    info     style advice worth knowing, safe to ignore

Rule ids are stable and never reused, so a suppression comment or a CI allowlist
can outlive a refactor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .frontmatter import Frontmatter

# Specification limits, quoted from the Agent Skills specification.
NAME_MAX = 64
DESCRIPTION_MAX = 1024
COMPATIBILITY_MAX = 500
BODY_LINE_SOFT_LIMIT = 500

KNOWN_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}

_NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Phrases that signal "this description says when to use the skill". A skill
# without any of these is usually a skill that never fires, because the
# description is the only thing the agent sees before deciding to load it.
TRIGGER_PHRASES = (
    "use when",
    "use this",
    "use it when",
    "use for",
    "when the user",
    "when you",
    "when a user",
    "trigger",
    "invoke",
    "适用于",
    "用于",
    "当用户",
)

VAGUE_OPENERS = (
    "helps with",
    "help with",
    "helps you",
    "a skill for",
    "utilities for",
    "tools for",
    "用于处理",
    "帮助",
)


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    message: str
    hint: str = ""
    line: int | None = None

    def __str__(self) -> str:
        location = f":{self.line}" if self.line is not None else ""
        return f"{self.severity}: [{self.rule}] {self.message}{location}"


@dataclass
class Skill:
    """One skill on disk, ready to be checked."""

    path: Path
    directory_name: str
    frontmatter: Frontmatter
    source_text: str

    @property
    def name(self) -> str | None:
        value = self.frontmatter.get("name")
        return value if isinstance(value, str) else None

    @property
    def description(self) -> str | None:
        value = self.frontmatter.get("description")
        return value if isinstance(value, str) else None

    @property
    def body(self) -> str:
        return self.frontmatter.body


def _line_of(source: str, needle: str) -> int | None:
    """Best-effort line number for a string that appears in the file."""
    if not needle:
        return None
    for index, line in enumerate(source.splitlines(), start=1):
        if needle in line:
            return index
    return None


def check_name(skill: Skill) -> list[Finding]:
    findings: list[Finding] = []
    name = skill.name

    if name is None:
        findings.append(
            Finding(
                "SV001",
                "error",
                "frontmatter is missing a `name` field",
                "Add `name:` to the frontmatter. It must equal the directory name.",
            )
        )
        return findings

    if not name:
        findings.append(
            Finding("SV001", "error", "`name` is empty", "Set it to the directory name.")
        )
        return findings

    if len(name) > NAME_MAX:
        findings.append(
            Finding(
                "SV002",
                "error",
                f"`name` is {len(name)} characters, the limit is {NAME_MAX}",
                "Shorten the name. Prefer two or three words.",
            )
        )

    if not _NAME_PATTERN.match(name):
        reasons = []
        if name != name.lower():
            reasons.append("it contains uppercase letters")
        if "_" in name:
            reasons.append("it contains underscores")
        if " " in name:
            reasons.append("it contains spaces")
        if "." in name:
            reasons.append("it contains dots")
        if name.startswith("-") or name.endswith("-"):
            reasons.append("it starts or ends with a hyphen")
        if "--" in name:
            reasons.append("it contains consecutive hyphens")
        detail = "; ".join(reasons) if reasons else "it is outside a-z, 0-9 and hyphen"
        findings.append(
            Finding(
                "SV003",
                "error",
                f"`name` uses characters the specification does not allow: {detail}",
                "Use lowercase letters, digits and single hyphens only, "
                f"for example `{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}`.",
            )
        )

    if name != skill.directory_name:
        findings.append(
            Finding(
                "SV006",
                "error",
                f"`name` is `{name}` but the directory is `{skill.directory_name}`",
                "The two must match exactly, otherwise the skill may not be "
                "discovered.",
            )
        )

    return findings


def check_description(skill: Skill) -> list[Finding]:
    findings: list[Finding] = []
    description = skill.description

    if description is None:
        findings.append(
            Finding(
                "SV007",
                "error",
                "frontmatter is missing a `description` field",
                "Without a description the agent has nothing to match a request "
                "against, so the skill never loads.",
            )
        )
        return findings

    if not description.strip():
        findings.append(
            Finding(
                "SV007",
                "error",
                "`description` is empty",
                "Say what the skill does and when to use it.",
            )
        )
        return findings

    if len(description) > DESCRIPTION_MAX:
        findings.append(
            Finding(
                "SV008",
                "error",
                f"`description` is {len(description)} characters, the limit is "
                f"{DESCRIPTION_MAX}",
                "Move the detail into the body. The description is loaded for "
                "every skill on every turn, so it is the most expensive text "
                "in the file.",
            )
        )

    lowered = description.lower()

    if not any(phrase in lowered for phrase in TRIGGER_PHRASES):
        findings.append(
            Finding(
                "SV009",
                "warning",
                "`description` never says when the skill should be used",
                "Add an explicit trigger, for example "
                "\"Use when the user asks to ...\". The description is the only "
                "text the agent sees before deciding whether to load the body.",
            )
        )

    if any(lowered.startswith(opener) for opener in VAGUE_OPENERS):
        findings.append(
            Finding(
                "SV010",
                "warning",
                "`description` opens with a vague phrase that matches almost "
                "any request",
                "Lead with the concrete object and action instead: "
                "\"Extracts tables from PDFs\" beats \"Helps with documents\".",
            )
        )

    if len(description.strip()) < 40:
        findings.append(
            Finding(
                "SV011",
                "warning",
                f"`description` is only {len(description.strip())} characters",
                "Short descriptions tend to under-trigger. Name the task, the "
                "artifact, and the trigger condition.",
            )
        )

    if "```" in description or "\n" in description.strip():
        findings.append(
            Finding(
                "SV007",
                "error",
                "`description` contains a code fence or a newline",
                "Keep it to a single line of plain prose. Use the body for "
                "structure and examples.",
            )
        )

    return findings


def check_optional_fields(skill: Skill) -> list[Finding]:
    findings: list[Finding] = []
    data = skill.frontmatter.data

    compatibility = data.get("compatibility")
    if isinstance(compatibility, str) and len(compatibility) > COMPATIBILITY_MAX:
        findings.append(
            Finding(
                "SV012",
                "error",
                f"`compatibility` is {len(compatibility)} characters, the limit is "
                f"{COMPATIBILITY_MAX}",
                "State only the hard requirements: product name, system packages, "
                "network access.",
            )
        )

    metadata = data.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        findings.append(
            Finding(
                "SV013",
                "error",
                "`metadata` must be a mapping of string keys to string values",
                "Example: `metadata:\\n  author: your-name\\n  version: \"1.0\"`",
            )
        )

    allowed_tools = data.get("allowed-tools")
    if allowed_tools is not None and not isinstance(allowed_tools, str):
        findings.append(
            Finding(
                "SV014",
                "error",
                "`allowed-tools` must be a space-separated string",
                "Example: `allowed-tools: Bash(git:*) Read`",
            )
        )

    for key in data:
        if key not in KNOWN_KEYS:
            findings.append(
                Finding(
                    "SV015",
                    "info",
                    f"unknown frontmatter key `{key}`",
                    "Unknown keys are ignored by most implementations. If the "
                    "value is meant for tooling, put it under `metadata`.",
                )
            )

    return findings


def check_body(skill: Skill) -> list[Finding]:
    findings: list[Finding] = []
    body = skill.body.strip()

    if not body:
        findings.append(
            Finding(
                "SV016",
                "error",
                "the body after the frontmatter is empty",
                "The body is what the agent reads after deciding to load the "
                "skill. An empty body makes the skill useless.",
            )
        )
        return findings

    line_count = skill.frontmatter.body_line_count
    if line_count > BODY_LINE_SOFT_LIMIT:
        findings.append(
            Finding(
                "SV017",
                "warning",
                f"the body is {line_count} lines, above the recommended "
                f"{BODY_LINE_SOFT_LIMIT}",
                "Move reference material into `references/` and link to it. The "
                "whole body is loaded at once, so length is a context cost paid "
                "on every activation.",
            )
        )

    if not re.search(r"^#{1,3}\s+\S", body, re.MULTILINE):
        findings.append(
            Finding(
                "SV018",
                "info",
                "the body has no Markdown heading",
                "A single `#` title makes the skill easier to skim and easier to "
                "diff later.",
            )
        )

    return findings


def check_references(skill: Skill) -> list[Finding]:
    """Check relative links in the body point at files that exist, one level deep."""
    findings: list[Finding] = []
    body = skill.body

    # Markdown links plus bare paths that look like a script invocation.
    link_pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    for match in link_pattern.finditer(body):
        target = match.group(1).strip().split("#", 1)[0].split("?", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        if target.startswith("/"):
            findings.append(
                Finding(
                    "SV019",
                    "warning",
                    f"reference `{target}` is an absolute path",
                    "Use a path relative to the skill directory so the skill "
                    "stays portable.",
                )
            )
            continue

        parts = Path(target).parts
        if len(parts) > 2:
            findings.append(
                Finding(
                    "SV020",
                    "warning",
                    f"reference `{target}` is nested more than one level deep",
                    "Keep references one level from SKILL.md, for example "
                    "`references/REFERENCE.md`. Deep chains are hard for the "
                    "agent to follow and hard for you to keep valid.",
                )
            )

        resolved = (skill.path.parent / target).resolve()
        if not resolved.exists():
            findings.append(
                Finding(
                    "SV021",
                    "error",
                    f"reference `{target}` does not exist on disk",
                    "Broken links send the agent into a dead end. Create the "
                    "file or drop the link.",
                )
            )

    return findings


def check_scripts(skill: Skill) -> list[Finding]:
    """Warn about scripts that no instruction ever mentions."""
    findings: list[Finding] = []
    scripts_dir = skill.path.parent / "scripts"
    if not scripts_dir.is_dir():
        return findings

    body = skill.body
    for script in sorted(scripts_dir.rglob("*")):
        if not script.is_file() or script.name.startswith("."):
            continue
        if script.name not in body:
            findings.append(
                Finding(
                    "SV022",
                    "warning",
                    f"`scripts/{script.name}` exists but the body never mentions it",
                    "An unreferenced script is dead weight. Either call it out "
                    "in the instructions or delete it.",
                )
            )

    return findings


ALL_RULES = (
    check_name,
    check_description,
    check_optional_fields,
    check_body,
    check_references,
    check_scripts,
)


def run_all(skill: Skill) -> list[Finding]:
    findings: list[Finding] = []
    for rule in ALL_RULES:
        findings.extend(rule(skill))
    return findings