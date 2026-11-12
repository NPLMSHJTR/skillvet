"""Parse the YAML frontmatter block at the top of a SKILL.md file.

The Agent Skills specification requires every SKILL.md to start with a YAML
frontmatter block delimited by `---`. This module isolates that parsing step so
the rest of the checker never has to think about text boundaries.

PyYAML is used when it is installed. When it is not, a deliberately small
fallback parser handles the flat key/value shape that skills actually use, so
the tool can run with zero third-party dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # pragma: no cover - exercised only by the dependency-free install path
    import yaml as _yaml
except ImportError:  # pragma: no cover
    _yaml = None


class FrontmatterError(Exception):
    """Raised when the frontmatter block is missing or cannot be parsed."""


@dataclass
class Frontmatter:
    """The parsed frontmatter plus the body that follows it."""

    data: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    raw: str = ""
    used_fallback_parser: bool = False

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    @property
    def body_line_count(self) -> int:
        return len(self.body.splitlines())


_DELIMITER = re.compile(r"^---[ \t]*$")
_KEY_LINE = re.compile(r"^([A-Za-z0-9_.-]+)[ \t]*:[ \t]*(.*)$")


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_text, body_text).

    The opening delimiter must be the very first line. A leading byte-order mark
    and leading blank lines are tolerated because editors add them silently and
    a linter that fails on an invisible character is a linter people uninstall.
    """
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1

    if start >= len(lines) or not _DELIMITER.match(lines[start]):
        raise FrontmatterError(
            "no frontmatter block found: SKILL.md must begin with a '---' line"
        )

    for index in range(start + 1, len(lines)):
        if _DELIMITER.match(lines[index]):
            frontmatter_text = "\n".join(lines[start + 1 : index])
            body_text = "\n".join(lines[index + 1 :])
            return frontmatter_text, body_text

    raise FrontmatterError(
        "unterminated frontmatter: found an opening '---' but no closing '---'"
    )


def _strip_inline_comment(value: str) -> str:
    """Drop a trailing ` # comment` that is not inside quotes."""
    quote: str | None = None
    for index, char in enumerate(value):
        if quote:
            if char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == "#" and index > 0 and value[index - 1] in " \t":
            return value[:index].rstrip()
    return value


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        inner = value[1:-1]
        if value[0] == '"':
            inner = (
                inner.replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\\\\", "\\")
            )
        else:
            inner = inner.replace("''", "'")
        return inner
    return value


def _coerce_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    if lowered in ("null", "~", ""):
        return None
    return value


def _parse_fallback(frontmatter_text: str) -> dict[str, Any]:
    """Parse the flat subset used by skills: scalars and one nested map level."""
    data: dict[str, Any] = {}
    current_map: dict[str, Any] | None = None
    current_key: str | None = None

    for raw_line in frontmatter_text.split("\n"):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        stripped = raw_line.rstrip()
        indented = stripped[:1] in (" ", "\t")

        if indented and current_map is not None:
            match = _KEY_LINE.match(stripped.strip())
            if match:
                key, value = match.group(1), _strip_inline_comment(match.group(2))
                current_map[key] = _coerce_scalar(_unquote(value))
                continue
            continue

        match = _KEY_LINE.match(stripped)
        if not match:
            continue

        key, value = match.group(1), _strip_inline_comment(match.group(2))
        if value.strip() == "":
            current_map = {}
            data[key] = current_map
            current_key = key
            continue

        current_map = None
        current_key = None
        data[key] = _coerce_scalar(_unquote(value))

    del current_key  # only relevant while walking indented lines
    return data


def load(path: Path) -> Frontmatter:
    """Read and parse a SKILL.md file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter_text, body = split_frontmatter(text)

    if _yaml is not None:
        try:
            parsed = _yaml.safe_load(frontmatter_text)
        except Exception as exc:  # noqa: BLE001 - surfaced as a lint finding
            raise FrontmatterError(f"frontmatter is not valid YAML: {exc}") from exc
        if parsed is None:
            parsed = {}
        if not isinstance(parsed, dict):
            raise FrontmatterError(
                "frontmatter must be a mapping of keys to values, "
                f"got {type(parsed).__name__}"
            )
        return Frontmatter(data=parsed, body=body, raw=frontmatter_text)

    return Frontmatter(
        data=_parse_fallback(frontmatter_text),
        body=body,
        raw=frontmatter_text,
        used_fallback_parser=True,
    )