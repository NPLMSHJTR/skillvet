# Anti-patterns

Twelve failure modes, each with the broken version, the fixed version, and the
rule that catches it. These are ordered by how often they actually appear.

---

## 1. The description that describes nothing in particular

**Rule SV010, SV009**

```yaml
# broken
description: Helps with data.
```

```yaml
# fixed
description: Profiles a CSV file and reports column types, null rates, and
  duplicate rows. Use when the user asks to inspect or clean up a data file.
```

`Helps with data` matches a spreadsheet request, a database question, and a
machine learning problem. It will fire on all three and help with none.

A fixed description names an artifact (a CSV file), an action (profile it), and
an occasion (when the user wants to inspect or clean data).

---

## 2. The description that only says what it does

**Rule SV009**

```yaml
# broken
description: PDF table extraction.
```

```yaml
# fixed
description: Extracts tables from PDF files and writes them to CSV, preserving
  header rows. Use when the user asks to pull tabular data out of a PDF.
```

This is the single most common failure. The description is accurate and
completely inert: it answers "what" but the loader asks "should I load this now".

---

## 3. The frontmatter that does not match its directory

**Rule SV006**

```
skills/pdf-tables/SKILL.md
---
name: pdf-table-extractor
---
```

Broken, silently. The loader finds the directory, reads the file, and now carries
two names for the same thing. Invocation by either name may fail depending on
implementation, and nothing reports an error.

```
skills/pdf-tables/SKILL.md
---
name: pdf-tables
---
```

**This one shipped in OpenAI's own repository.** `code-review-breaking-changes/`
declares `name: code-breaking-changes`. It is why this rule is an error and why
it belongs in CI rather than in a style guide.

---

## 4. The 400-line skill that contains one rule

**Rule SV017**

```markdown
# Change size policy

## Background
Our engineering organisation has grown...

## Why change size matters
Large changes are harder to review... (300 words)

## Historical context
In 2019 the team decided... (200 words)

## The rule
Changes should not exceed 800 lines.

## Exceptions
Mechanical changes such as renames are exempt.

## How to check
Count the lines in the diff...
```

The rule is one sentence in the middle of a document about the rule. A model
reading this spends its attention on the prose and may or may not extract the
number.

The alternative, measured from the real file:

```markdown
---
name: code-review-change-size
description: Change size guidance (800 lines)
---

Unless the change is mechanical the total number of changed lines should not
exceed 800 lines. For complex logic changes the size should be under 500 lines.

If the change is larger, explain whether it can be split into reviewable stages
and identify the smallest coherent stage to land first.
```

Six lines. The number, the exception, and the required behaviour when the rule
is violated. Nothing else.

**The background belongs in a design document, not in a skill.** The skill is
the instruction; the reasoning is what you write when someone asks why.

---

## 5. The one skill that does five things

**Rule SV017, SV009**

```yaml
name: code-quality
description: Reviews code for bugs, performance, security, style, test coverage,
  documentation, accessibility, and maintainability. Use when reviewing code.
```

Every clause in that description is a dimension that deserves attention. A single
pass will check whichever dimension the model finds easiest and skim the rest.

The measured alternative splits into four skills of 336 to 673 bytes each, plus
a 666-byte orchestrator that gives each one a subagent. Total size is larger.
Total attention per dimension is larger too, and that is the number that matters.

---

## 6. The absolute path

**Rule SV019**

```markdown
See [the reference](/Users/me/projects/skill-notes/REFERENCE.md).
```

Works on exactly one machine, on exactly one day.

```markdown
See [the reference](references/REFERENCE.md).
```

---

## 7. The reference chain

**Rule SV020**

```
SKILL.md → references/advanced.md → details/deep/impl.md → impl-notes.md
```

Each hop is a path the agent has to resolve and you have to maintain. When the
middle link renames, the failure is silent.

Flatten it: `references/impl.md`, linked directly from `SKILL.md`.

---

## 8. The skill with a broken link

**Rule SV021**

```markdown
Run `scripts/extract.py` to pull the tables.
```

Where `scripts/` does not exist. The agent will not report this. It will either
improvise a worse approach or claim success without doing the work — and you will
find out from the output, days later.

---

## 9. The script nobody calls

**Rule SV022**

```
skills/pdf-tables/
├── SKILL.md          # never mentions the script
└── scripts/
    └── extract.py
```

Either the instructions are incomplete or the script is dead. Both are worth
fixing; the ambiguity is the problem.

---

## 10. The version field that lies

**Rule SV015**

```yaml
name: pdf-tables
description: ...
version: 2.1.0
```

Nobody updates it. Six months later, `version: 2.1.0` and `git log` disagree, and
there is no way to tell which one is right without reading the history.

Put versioning in tags, where it is maintained by the act of releasing. If a tool
genuinely needs it, put it under `metadata` and generate it.

---

## 11. The description used as documentation

**Rule SV008**

```yaml
description: >
  This skill handles PDFs. It supports extraction of text, tables, and images.
  It can also fill forms, merge documents, and split files. It handles
  password-protected files, scanned documents via OCR, and...
```

Every skill in the directory pays for this. `name` and `description` load on
every turn for every skill; the body loads only after a match.

At 900 characters this one description costs more context than three complete
skills. Move the capability list into the body, where it waits until someone
actually needs it.

---

## 12. The trigger phrase in the wrong place

**Rule SV009**

```yaml
description: Extracts PDF tables.
```

```markdown
# PDF tables

Use this skill when the user asks to extract tables from a PDF.
```

The trigger is in the body. The body is only read *after* the loader decides the
skill matches. The instruction that would have caused the match is unreachable
until the match happens.

```yaml
description: Extracts PDF tables. Use when the user asks to extract tables
  from a PDF.
```

This one is worth internalising because it is a category error rather than a
style mistake: the skill explains how to be chosen, in the one place that is
never read during choosing.

---

## The pattern behind all twelve

Nine of these are the same mistake in different clothes: **treating a skill as a
document to be written rather than an instruction to be executed.**

A document explains. An instruction acts. The frontmatter answers one question;
the body answers another; and text placed in the wrong one of the two is not
merely unhelpful, it is unreachable.

The remaining three — mismatched name, broken link, dead script — are what
happens when correctness depends on human attention instead of a check. Which is
the argument for running `skillvet` in CI, and the reason this tool exists.