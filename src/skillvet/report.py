"""Output rendering: human-readable text and machine-readable JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .rules import Finding, Skill

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass
class Result:
    skill: Skill | None
    path: Path
    findings: list[Finding]
    fatal: str | None = None

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "info")

    def sorted_findings(self) -> list[Finding]:
        return sorted(
            self.findings,
            key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.rule),
        )


def render_text(results: list[Result], base: Path, color: bool) -> str:
    lines: list[str] = []

    def paint(text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if color else text

    red = lambda t: paint(t, "31")       # noqa: E731
    yellow = lambda t: paint(t, "33")    # noqa: E731
    blue = lambda t: paint(t, "36")      # noqa: E731
    dim = lambda t: paint(t, "2")        # noqa: E731
    bold = lambda t: paint(t, "1")       # noqa: E731

    for result in results:
        try:
            display = result.path.relative_to(base)
        except ValueError:
            display = result.path

        name = result.skill.directory_name if result.skill else display.parent.name

        if result.fatal:
            lines.append(f"{red('E')} {bold(str(display))}")
            lines.append(f"    {red('error')} {result.fatal}")
            lines.append("")
            continue

        ordered = result.sorted_findings()
        if not ordered:
            lines.append(f"{paint('P', '32')} {bold(str(display))}")
            lines.append(f"    {dim('no findings')}")
            lines.append("")
            continue

        marker = red("E") if result.error_count else (
            yellow("W") if result.warning_count else blue("I")
        )
        counts = []
        if result.error_count:
            counts.append(red(f"{result.error_count} error"))
        if result.warning_count:
            counts.append(yellow(f"{result.warning_count} warning"))
        if result.info_count:
            counts.append(blue(f"{result.info_count} info"))
        summary = ", ".join(counts)
        lines.append(f"{marker} {bold(str(display))} {dim(f'({name})')} — {summary}")

        for finding in ordered:
            if finding.severity == "error":
                label = red("error")
            elif finding.severity == "warning":
                label = yellow("warn")
            else:
                label = blue("info")
            location = f" {dim(f'line {finding.line}')}" if finding.line else ""
            lines.append(f"    {label} {dim(finding.rule)} {finding.message}{location}")
            if finding.hint:
                for hint_line in finding.hint.split("\n"):
                    lines.append(f"         {dim(hint_line)}")
        lines.append("")

    total = len(results)
    failed = sum(1 for r in results if r.fatal or r.error_count)
    warned = sum(1 for r in results if not r.fatal and not r.error_count and r.warning_count)
    clean = total - failed - warned

    parts = [f"{total} skill{'s' if total != 1 else ''} checked"]
    if failed:
        parts.append(red(f"{failed} failed"))
    if warned:
        parts.append(yellow(f"{warned} with warnings"))
    if clean:
        parts.append(paint(f"{clean} clean", "32"))

    lines.append(bold(" · ".join(parts)))
    return "\n".join(lines)


def render_json(results: list[Result], base: Path) -> str:
    payload = {
        "skills": [],
        "summary": {
            "total": len(results),
            "failed": 0,
            "warnings": 0,
            "clean": 0,
            "errors": 0,
        },
    }

    for result in results:
        try:
            display = str(result.path.relative_to(base))
        except ValueError:
            display = str(result.path)

        entry = {
            "path": display,
            "name": result.skill.directory_name if result.skill else None,
            "fatal": result.fatal,
            "findings": [
                {
                    "rule": f.rule,
                    "severity": f.severity,
                    "message": f.message,
                    "hint": f.hint,
                    "line": f.line,
                }
                for f in result.sorted_findings()
            ],
        }
        payload["skills"].append(entry)

        payload["summary"]["errors"] += result.error_count
        if result.fatal or result.error_count:
            payload["summary"]["failed"] += 1
        elif result.warning_count:
            payload["summary"]["warnings"] += 1
        else:
            payload["summary"]["clean"] += 1

    return json.dumps(payload, indent=2, ensure_ascii=False)