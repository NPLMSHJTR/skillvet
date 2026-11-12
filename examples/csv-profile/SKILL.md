---
name: csv-profile
description: Profiles a CSV file and reports column types, null rates, distinct counts, and duplicate rows. Use when the user asks to inspect, sanity-check, or summarize the shape of a CSV or TSV file before analyzing it.
license: MIT
---

# CSV profile

Answer "what is actually in this file" before anyone writes a query against it.
The output is a short report, not a full statistical summary.

## Steps

1. Run the profiler and capture its JSON output:

   ```bash
   python scripts/profile.py <path-to-file>
   ```

2. Report as a Markdown table, one row per column, in the file's original column
   order. Columns: `name`, `inferred type`, `null %`, `distinct`, `example`.

3. After the table, report three things in plain sentences:

   - total rows and columns
   - any column with more than 20% nulls
   - any fully duplicated row, with the count

4. If the delimiter is not a comma, say which one was detected and how. The
   profiler reports it in the `delimiter` field.

## Rules

- Never guess a value you did not measure. If the profiler errors on a row, say
  so and report how many rows it managed to read.
- Report nulls as a percentage of the rows actually read, and state that
  denominator. It is usually smaller than the row count.
- Do not recommend a type change. Report what was inferred and stop; the
  decision depends on how the data will be used, which you do not know yet.

## Reference

Type inference rules, including how mixed columns are resolved, are in
[references/type-inference.md](references/type-inference.md).

## When the file is large

Above roughly 500 MB the profiler samples instead of reading everything. It
reports `sampled: true` and the sample size. Say so in your report — a sampled
profile is evidence, not proof.