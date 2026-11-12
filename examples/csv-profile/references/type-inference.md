# Type inference rules

The profiler infers the narrowest type that fits every non-empty value in a
column. This file records the exact rules so a report can be checked without
reading the source.

## Order of checks

Types are tested in this order, and the first match wins:

1. `empty` — every value is blank
2. `integer` — every value parses as `int`
3. `float` — every value parses as `float`
4. `boolean` — every value is one of `true`, `false`, `yes`, `no`, `0`, `1`
   (case-insensitive)
5. `date` — every value parses as one of the formats below
6. `text` — anything else

Order matters in two places:

- A column of `0` and `1` is **integer**, not boolean, because integer is tested
  first. This is deliberate: a numeric flag is usually arithmetic, and calling
  it boolean would invite a type change that breaks sums.
- A column of integers is not float even though integers parse as floats,
  because integer is tested first.

## Numeric parsing

Commas inside numbers are removed before parsing, so `1,234` is an integer.
This means a column containing both `1,234` and `1.5` infers as `float`, and a
column of European-style `1.234,56` values infers as `text`. Both are reported
as they were measured; the profiler does not guess a locale.

Leading and trailing whitespace is stripped before parsing but is **not**
reported as a null. A column of `" "` values is `empty`, a column of `""` is
`empty`, and a column with neither is profiled on its real values.

## Date formats recognised

| format | example |
| --- | --- |
| `%Y-%m-%d` | `2026-11-12` |
| `%Y/%m/%d` | `2026/11/12` |
| `%d/%m/%Y` | `12/11/2026` |
| `%Y-%m-%dT%H:%M:%S` | `2026-11-12T13:35:44` |

A column mixing formats infers as `text`. So does a column of dates with a
leading zero that does not match, such as `2026-1-5`.

There is no timezone handling. A datetime with an offset is `text`.

## Null counting

A value counts as null when `value.strip()` is empty. That covers `""`, `" "`,
and `"\t"`.

It does **not** cover the strings `NA`, `N/A`, `null`, or `-`. Those are
`text`, and the null percentage will under-report. This is the most common way
the reported null rate is wrong, so it is worth stating in any report: the
number measures blank cells, not missing values.

## Mixed columns

There is no majority vote. One non-conforming value makes the column `text`.
A column of 999 integers and a single `n/a` is `text`.

That is stricter than most profilers and intentionally so: silently dropping
outliers is how a type inference becomes a lie.

## Sampling

Above 1,000,000 rows the profiler stops reading and sets `sampled: true`. All
percentages are then relative to rows actually read, not the file's true length.

`--sample-rows N` overrides the threshold for testing.