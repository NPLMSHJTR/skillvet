# Contributing

Two kinds of contribution are most useful, and they are not equal.

## 1. A skill this tool misjudges (most useful)

If `skillvet` flags a skill that is actually fine, that is a bug. It is more
valuable than a feature request, because a linter's only real asset is its
credibility and a false positive spends it.

Open an issue with:

- the `SKILL.md` frontmatter (redact anything private)
- the rule id that fired
- what the skill is supposed to do
- what you think the rule should have said

A concrete skill beats a description of a category. "SV009 fires on this" is
actionable; "SV009 has false positives" is not.

## 2. A new rule

Rules are added, never changed in place, and rule ids are never reused. That
means a suppression list written today will still mean something in a year.

A rule proposal should answer four questions in the issue before any code:

1. What does the bad skill look like?
2. What does the good version look like?
3. What breaks in production if you get it wrong?
4. Why can this be checked statically, rather than by reading the skill?

Question 4 is the one that disqualifies most proposals. "This skill is badly
written" is not statically checkable. "This skill's `name` does not match its
directory" is.

## Adding a rule

```
1. Pick the next free SV0xx id.
2. Write a function in src/skillvet/rules.py that returns list[Finding].
3. Register it in ALL_RULES.
4. Add a test with a case that should fire and a case that should not.
5. Document it in docs/rules.md: the rule, why it exists, bad vs good.
6. If it reflects a new real-world failure, add it to docs/anti-patterns.md.
```

Every rule needs both tests. A rule with only a positive case is a rule that has
not been shown to avoid false positives.

## Severity

Be conservative. This is the whole design:

- **error** — the file violates the Agent Skills specification, or will not
  load. There must be a citation.
- **warning** — the skill will work but probably under-trigger. Judgment is
  involved, so it is never fatal by default.
- **info** — style advice. Somebody has to be able to ignore it without thinking
  about it.

If you are unsure between error and warning, choose warning. A linter that fails
a build over a guess gets uninstalled, and then it catches nothing.

## Code

- Python 3.9 compatible. No f-string `=` specifiers, no `match`, no `X | Y` in
  runtime-evaluated annotations (use `from __future__ import annotations`).
- Standard library only for the core tool. PyYAML is an optional extra and must
  stay optional — CI runs the test suite without it.
- Tests: `python -m pytest`
- Before submitting: `python -m skillvet examples --strict` must pass.

## Docs

Claims about the specification must cite it. If you write "the limit is 1024
characters", link where that came from. Uncited numbers are how a linter starts
enforcing someone's memory.

Claims about what real projects do must be measured, with the method stated.
`docs/field-notes.md` is the model: snapshot date, retrieval method, raw counts,
and a note when something cannot be verified.

## What is out of scope

- Plugin manifests and marketplace files. A future tool, not this one.
- Running skills to observe behaviour. This is a static checker by design;
  running arbitrary skill scripts to grade them is a different project with a
  different threat model.
- Style opinions with no failure mode behind them. If you cannot say what breaks,
  it belongs in a blog post.