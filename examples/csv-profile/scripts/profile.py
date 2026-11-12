#!/usr/bin/env python3
"""Profile a CSV/TSV file: column types, null rates, distinct counts, duplicates.

Standard library only, so the skill works on any machine with Python 3.9+.

    python profile.py data.csv
    python profile.py data.csv --sample-rows 50000
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

SAMPLE_THRESHOLD_ROWS = 1_000_000


def sniff_delimiter(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        sample = handle.read(8192)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def infer_type(values: list[str]) -> str:
    """Infer the narrowest type that fits every non-empty value."""
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return "empty"

    def all_match(predicate) -> bool:
        return all(predicate(v) for v in non_empty)

    def is_int(v: str) -> bool:
        try:
            int(v.replace(",", ""))
            return True
        except ValueError:
            return False

    def is_float(v: str) -> bool:
        try:
            float(v.replace(",", ""))
            return True
        except ValueError:
            return False

    def is_bool(v: str) -> bool:
        return v.strip().lower() in ("true", "false", "yes", "no", "0", "1")

    def is_date(v: str) -> bool:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                datetime.strptime(v.strip(), fmt)
                return True
            except ValueError:
                continue
        return False

    if all_match(is_int):
        return "integer"
    if all_match(is_float):
        return "float"
    if all_match(is_bool):
        return "boolean"
    if all_match(is_date):
        return "date"
    return "text"


def profile(path: Path, sample_rows: int | None) -> dict:
    delimiter = sniff_delimiter(path)
    truncated = False

    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration:
            return {"error": "file is empty", "delimiter": delimiter}

        columns: list[list[str]] = [[] for _ in header]
        row_count = 0
        seen: set[tuple[str, ...]] = set()
        duplicate_rows = 0
        limit = SAMPLE_THRESHOLD_ROWS if sample_rows is None else sample_rows

        for row in reader:
            if row_count >= limit:
                truncated = True
                break
            row_count += 1
            padded = row + [""] * (len(header) - len(row))
            for index, value in enumerate(padded[: len(header)]):
                columns[index].append(value)
            key = tuple(padded[: len(header)])
            if key in seen:
                duplicate_rows += 1
            else:
                seen.add(key)

    fields = []
    for name, values in zip(header, columns):
        non_empty = [v for v in values if v.strip()]
        nulls = len(values) - len(non_empty)
        fields.append(
            {
                "name": name,
                "type": infer_type(values),
                "null_count": nulls,
                "null_pct": round(nulls / row_count * 100, 2) if row_count else 0.0,
                "distinct": len(set(non_empty)),
                "example": non_empty[0] if non_empty else "",
            }
        )

    return {
        "path": str(path),
        "delimiter": "tab" if delimiter == "\t" else delimiter,
        "rows_read": row_count,
        "sampled": truncated,
        "duplicate_rows": duplicate_rows,
        "columns": fields,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=None,
        help=f"stop after N rows (default: {SAMPLE_THRESHOLD_ROWS} before sampling)",
    )
    args = parser.parse_args(argv)

    if not args.path.is_file():
        print(f"error: no such file: {args.path}", file=sys.stderr)
        return 1

    try:
        result = profile(args.path, args.sample_rows)
    except Exception as exc:  # noqa: BLE001 - reported to the caller
        print(f"error: could not read {args.path}: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    raise SystemExit(main())