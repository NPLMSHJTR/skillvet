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

    # Integers and floats, so the fallback matches PyYAML. A version string
    # like "1.0" is normally quoted by skill authors precisely to avoid this;
    # _unquote runs before this function, so a quoted value stays a string.
    try:
        return int(value, 10)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass

    return value


def _parse_fallback(frontmatter_text: str) -> dict[str, Any]:
    """Parse the flat subset used by skills: scalars and one nested map level.

    Anything outside that subset raises FrontmatterError rather than being
    skipped. Silently ignoring a line is how a malformed frontmatter becomes a
    skill with an empty name, which then fails somewhere far away from the
    actual mistake.
    """
    data: dict[str, Any] = {}
    current_map: dict[str, Any] | None = None
    block_scalar: tuple[str, list[str], str] | None = None  # (style, lines, key)
    # A block list, e.g. allowed-tools written as "- Bash" lines. Skills do
    # contain these, and a rule (SV014) exists to explain them, so the parser
    # has to hand the list through instead of failing before the rule runs.
    current_list_key: str | None = None
    items: list[Any] = []
    # A `key:` line whose value is empty. What follows decides whether it is a
    # list, a nested map, or a null.
    pending_key: str | None = None

    def flush_block() -> None:
        nonlocal block_scalar
        if block_scalar is None:
            return
        style, collected, key = block_scalar
        if style == "|":
            text = "\n".join(collected)
        else:  # ">" folded
            text = " ".join(part for part in collected if part)
        data[key] = text.strip()
        block_scalar = None

    for raw_line in frontmatter_text.split("\n"):
        # While collecting a block scalar, indentation decides what belongs to it.
        if block_scalar is not None:
            style, collected, key = block_scalar
            if raw_line.strip() == "":
                collected.append("")
                continue
            if raw_line[:1] in (" ", "\t"):
                collected.append(raw_line.strip())
                continue
            flush_block()

        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        stripped = raw_line.rstrip()
        indented = stripped[:1] in (" ", "\t")

        if indented and current_list_key is not None:
            item = stripped.strip()
            if item.startswith("- "):
                items.append(_coerce_scalar(_unquote(item[2:].strip())))
                continue
            if item == "-":
                items.append(None)
                continue

        # An indented block that continues a `key:` with an empty value. It is
        # a list if it starts with "- ", otherwise a nested map.
        if indented and pending_key is not None:
            item = stripped.strip()
            if item.startswith("- "):
                data[pending_key] = []
                current_list_key = pending_key
                items = data[pending_key]
                pending_key = None
                items.append(_coerce_scalar(_unquote(item[2:].strip())))
                continue
            if item == "-":
                data[pending_key] = []
                current_list_key = pending_key
                items = data[pending_key]
                pending_key = None
                items.append(None)
                continue
            # Not a list, so treat it as the first entry of a nested map.
            current_map = {}
            data[pending_key] = current_map
            pending_key = None

        if indented and current_map is not None:
            match = _KEY_LINE.match(stripped.strip())
            if match:
                key, value = match.group(1), _strip_inline_comment(match.group(2))
                nested_quoted = (
                    len(value.strip()) >= 2
                    and value.strip()[0] == value.strip()[-1]
                    and value.strip()[0] in ("'", '"')
                )
                unquoted = _unquote(value)
                current_map[key] = (
                    unquoted if nested_quoted else _coerce_scalar(unquoted)
                )
                continue
            raise FrontmatterError(
                f"cannot parse frontmatter line: {stripped.strip()!r}"
            )

        match = _KEY_LINE.match(stripped)
        if not match:
            # A list item, a bare scalar, or anything else that is not a
            # key/value pair. The specification wants a mapping, so this is an
            # error and not something to skip.
            raise FrontmatterError(
                "frontmatter must be a mapping of keys to values; "
                f"this line is not a `key: value` pair: {stripped.strip()!r}"
            )

        key, value = match.group(1), _strip_inline_comment(match.group(2))
        if value.strip() in ("|", ">", "|-", ">-", "|+", ">+"):
            style = value.strip()[0]
            block_scalar = (style, [], key)
            current_map = None
            current_list_key = None
            pending_key = None
            continue

        if value.strip() == "":
            # Defer: the next indented line decides list vs map vs null.
            current_map = None
            current_list_key = None
            pending_key = key
            continue

        current_map = None
        current_list_key = None
        pending_key = None
        # Decide on the raw text: a quoted value keeps its type as a string,
        # so `version: '1.0'` must not become the float 1.0.
        is_quoted = (
            len(value.strip()) >= 2
            and value.strip()[0] == value.strip()[-1]
            and value.strip()[0] in ("'", '"')
        )
        # A plain scalar containing ": " is invalid YAML, and PyYAML rejects it.
        # Match that, so a skill that would fail to load in a real agent fails
        # here too, instead of being quietly accepted by the lenient parser.
        if not is_quoted and ": " in value:
            raise FrontmatterError(
                "frontmatter is not valid YAML: an unquoted value contains "
                f"': ', so quote the whole value: {stripped.strip()!r}"
            )
        unquoted = _unquote(value)
        data[key] = unquoted if is_quoted else _coerce_scalar(unquoted)

    flush_block()
    # A `key:` with nothing indented under it is a null value, like PyYAML.
    if pending_key is not None:
        data[pending_key] = None
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