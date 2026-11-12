"""Command line interface.

Exit codes are part of the contract, because the main consumer is CI:

    0  every skill passed
    1  at least one finding at or above the configured failure threshold
    2  usage error, or nothing was found to check
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .discovery import find_skill_files
from .frontmatter import FrontmatterError, load
from .report import Result, render_json, render_text
from .rules import Skill, run_all

SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillvet",
        description="Lint Agent Skills: check SKILL.md against the specification "
        "and against the patterns that stop skills from triggering.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="skill directory, SKILL.md file, or a directory to search recursively "
        "(default: current directory)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat warnings as failures, so the exit code is 1 if any warning "
        "is found",
    )
    parser.add_argument(
        "--no-info",
        action="store_true",
        help="hide info-level findings from the report",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print nothing except the summary line",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI colors (also disabled when NO_COLOR is set)",
    )
    parser.add_argument(
        "--version", action="version", version=f"skillvet {__version__}"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    roots = [Path(p) for p in args.paths]
    files = find_skill_files(roots)

    if not files:
        print(
            f"skillvet: no {('SKILL.md')} found under "
            + ", ".join(str(r) for r in roots),
            file=sys.stderr,
        )
        return 2

    results: list[Result] = []
    for path in files:
        try:
            frontmatter = load(path)
        except FrontmatterError as exc:
            results.append(Result(skill=None, path=path, findings=[], fatal=str(exc)))
            continue

        skill = Skill(
            path=path,
            directory_name=path.parent.name,
            frontmatter=frontmatter,
            source_text=path.read_text(encoding="utf-8", errors="replace"),
        )
        findings = run_all(skill)
        if args.no_info:
            findings = [f for f in findings if f.severity != "info"]
        results.append(Result(skill=skill, path=path, findings=findings))

    base = Path.cwd()
    color = sys.stdout.isatty() and not args.no_color and "NO_COLOR" not in __import__(
        "os"
    ).environ

    if args.format == "json":
        print(render_json(results, base))
    elif args.quiet:
        failed = sum(1 for r in results if r.fatal or r.error_count)
        warned = sum(1 for r in results if not r.fatal and not r.error_count and r.warning_count)
        print(
            f"{len(results)} checked · {failed} failed · {warned} with warnings · "
            f"{len(results) - failed - warned} clean"
        )
    else:
        print(render_text(results, base, color))

    threshold = SEVERITY_RANK["warning"] if args.strict else SEVERITY_RANK["error"]
    worst = SEVERITY_RANK["info"]
    for result in results:
        if result.fatal:
            return 1
        for finding in result.findings:
            worst = min(worst, SEVERITY_RANK.get(finding.severity, 9))

    return 1 if worst <= threshold else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())