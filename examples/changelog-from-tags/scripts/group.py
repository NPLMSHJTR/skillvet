#!/usr/bin/env python3
"""Group commits in a git range by Conventional Commit type.

    python group.py v1.2.0..v1.3.0
    python group.py                     # latest tag..HEAD, or last 50 commits

Outputs JSON on stdout so the calling agent can format it. Never edits files.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

TYPE_TO_GROUP = {
    "feat": "Added",
    "feature": "Added",
    "add": "Added",
    "fix": "Fixed",
    "bugfix": "Fixed",
    "hotfix": "Fixed",
    "refactor": "Changed",
    "perf": "Changed",
    "style": "Changed",
    "docs": "Changed",
    "build": "Other",
    "ci": "Other",
    "chore": "Other",
    "test": "Other",
    "revert": "Removed",
    "remove": "Removed",
    "deprecate": "Removed",
}

GROUP_ORDER = ["Breaking", "Added", "Changed", "Fixed", "Removed", "Other"]

# `type(scope)!: subject` or `type: subject`
CONVENTIONAL = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s*(?P<subject>.+)$")

UNIT = "\x1f"  # between fields
RECORD = "\x1e"  # between commits


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def latest_tag() -> str | None:
    try:
        out = run_git(["describe", "--tags", "--abbrev=0"]).strip()
        return out or None
    except RuntimeError:
        return None


def resolve_range(explicit: str | None) -> tuple[str, str]:
    """Return (range_spec, human_readable_description)."""
    if explicit:
        return explicit, explicit

    tag = latest_tag()
    if tag:
        return f"{tag}..HEAD", f"{tag}..HEAD (latest tag to HEAD)"

    return "-n 50", "last 50 commits (no tags found)"


def read_commits(range_spec: str) -> list[dict]:
    fmt = f"%H{UNIT}%s{UNIT}%an{UNIT}%cs{UNIT}%b{RECORD}"
    if range_spec.startswith("-n "):
        args = ["log", "-n", range_spec.split()[1], f"--pretty=format:{fmt}"]
    else:
        args = ["log", range_spec, f"--pretty=format:{fmt}"]

    raw = run_git(args)
    commits = []
    for record in raw.split(RECORD):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split(UNIT)
        if len(parts) < 5:
            continue
        sha, subject, author, date, body = parts[0], parts[1], parts[2], parts[3], parts[4]
        commits.append(
            {"sha": sha[:8], "subject": subject, "author": author, "date": date, "body": body}
        )
    return commits


def classify(commit: dict) -> dict:
    subject = commit["subject"]
    match = CONVENTIONAL.match(subject)

    is_breaking = "BREAKING CHANGE" in commit["body"].upper()

    if not match:
        return {
            **commit,
            "conventional": False,
            "type": None,
            "scope": None,
            "group": "Other",
            "breaking": is_breaking,
        }

    ctype = match.group("type").lower()
    group = TYPE_TO_GROUP.get(ctype, "Other")
    if match.group("bang"):
        is_breaking = True

    return {
        **commit,
        "conventional": True,
        "type": ctype,
        "scope": match.group("scope"),
        "group": "Breaking" if is_breaking else group,
        "breaking": is_breaking,
        "subject_clean": match.group("subject"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("range", nargs="?", help="git range, e.g. v1.2.0..v1.3.0")
    args = parser.parse_args(argv)

    try:
        range_spec, description = resolve_range(args.range)
        commits = read_commits(range_spec)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    classified = [classify(c) for c in commits]
    conventional_count = sum(1 for c in classified if c["conventional"])
    total = len(classified)

    groups: dict[str, list[dict]] = {name: [] for name in GROUP_ORDER}
    for commit in classified:
        groups[commit["group"]].append(commit)

    payload = {
        "range": range_spec,
        "range_description": description,
        "total_commits": total,
        "conventional_commits": conventional_count,
        "conventional_ratio": round(conventional_count / total, 2) if total else 0.0,
        "groups": {name: items for name, items in groups.items() if items},
        "group_order": GROUP_ORDER,
        "note": (
            "Fewer than half the commits follow Conventional Commits; the "
            "grouping is unreliable, prefer a flat list."
            if total and conventional_count / total < 0.5
            else None
        ),
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())