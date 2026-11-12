# Rules

Every rule, why it exists, and what breaks without it. The specification numbers
here come from the [Agent Skills specification](https://agentskills.io/specification).

A note on severity. **error** means the file violates the specification or will
not load. **warning** means it will load but is likely to under-trigger or
misbehave. **info** is style advice you are free to ignore.

---

## SV001 — `name` is present and non-empty

**error**

`name` is one of two required fields. Without it the skill has no identity and
cannot be addressed.

```yaml
# bad
---
description: Extracts tables from PDFs. Use when asked to pull tabular data.
---

# good
---
name: pdf-tables
description: Extracts tables from PDFs. Use when asked to pull tabular data.
---
```

---

## SV002 — `name` is at most 64 characters

**error**

The specification caps `name` at 64 characters.

At 64 characters you have long since lost the reader. If a name needs a second
conjunction to describe itself, it is probably two skills.

---

## SV003 — `name` uses only `a-z`, `0-9` and single hyphens

**error**

Rejected by the specification:

| input | why |
| --- | --- |
| `PDF-Tables` | uppercase |
| `pdf_tables` | underscore |
| `pdf tables` | space |
| `pdf.tables` | dot |
| `-pdf` | leading hyphen |
| `pdf-` | trailing hyphen |
| `pdf--tables` | consecutive hyphens |

`pdf-tables` is the only form that passes.

The reason is mechanical, not aesthetic: the name becomes a directory name, and
the loader matches one against the other. Every character class above is a
platform that will treat the path differently.

---

## SV006 — `name` equals the parent directory name

**error**

This is the rule that catches real bugs. The skill loader walks directories and
reads `SKILL.md`; the `name` field is what the model sees. If the two disagree,
you have built a skill you cannot invoke by the name you think it has.

A live example, from OpenAI's own repository:

```
directory: code-review-breaking-changes
name:      code-breaking-changes
```

That mismatch sat in a public repository used daily by the team that wrote the
specification.

---

## SV007 — `description` is present, non-empty, single-line

**error**

`description` is the second required field. It is also the only text the agent
sees before deciding whether to load the skill body, which makes it the single
highest-leverage string in the file.

Single-line matters because implementations vary in how they trim and match. A
description containing a newline or a code fence is either truncated or matched
against in ways you did not intend.

---

## SV008 — `description` is at most 1024 characters

**error**

The specification cap. This limit is generous on purpose; almost nothing good
lives between 300 and 1024 characters.

The cost is real: `name` and `description` are loaded for **every** skill on
**every** turn. A 1000-character description in a directory of 40 skills is
40,000 characters of metadata before the user has asked anything.

Move the detail into the body. The body is free until activation.

---

## SV009 — `description` states when to use the skill

**warning**

The most common real-world failure, and the reason this tool exists.

The loader does not read your skill looking for a reason to use it. It reads the
description and asks one question: does this match the request? A description
that says only *what* the skill does gives that question nothing to match on.

```yaml
# bad — describes the artifact, not the occasion
description: PDF table extraction.

# good — names the occasion
description: Extracts tables from PDF files and writes them to CSV. Use when
  the user asks to pull tabular data out of a PDF.
```

The phrase list is a heuristic: "use when", "use this", "when the user", "when
you", "trigger", "invoke", plus the Chinese equivalents 适用于 / 用于 / 当用户.
This is why the rule is a warning and not an error. A skill can trigger through
wording this list does not contain, and it would be wrong to fail a build over a
guess.

---

## SV010 — `description` does not open with a vague phrase

**warning**

Openers like "Helps with…", "A skill for…", "Tools for…" describe a category, and
a category matches nearly any request in that area. The result is a skill that
fires on the wrong thing, competes with its siblings, and then produces work the
user did not ask for.

```yaml
# bad
description: Helps with documents.

# good
description: Merges a folder of PDFs into one file with a table of contents.
  Use when the user asks to combine PDFs.
```

---

## SV011 — `description` is not too short to match on

**warning**

Under roughly 40 characters there is not enough text to distinguish this skill
from its neighbours. "Breaking changes" and "Change size guidance" both appear
in OpenAI's own skill set at 16 and 32 characters respectively, and both would
be near-unmatchable outside their narrow context.

Note the interaction with the orchestration pattern: short descriptions work
when a parent skill explicitly dispatches to named children. They fail when the
skill has to compete for attention in a general directory. The rule cannot tell
the two cases apart, so it warns.

---

## SV012 — `compatibility` is at most 500 characters

**error**

The specification cap. `compatibility` is for hard requirements only: product
name, system packages, network access.

```yaml
compatibility: Requires git, jq, and access to the internet
```

It is not a place for prose. Most skills do not need the field at all.

---

## SV013 — `metadata` is a string-to-string mapping

**error**

`metadata` is the extension point for tooling. Implementations expect a flat map
and will either drop or misread anything else.

```yaml
# good
metadata:
  author: your-name
  version: "1.0"
```

Nesting a list or a second level under `metadata` is the usual mistake.

---

## SV014 — `allowed-tools` is a space-separated string

**error**

A string, not a YAML list:

```yaml
# good
allowed-tools: Bash(git:*) Bash(jq:*) Read

# bad
allowed-tools:
  - Bash
  - Read
```

The field is marked experimental and support varies between implementations, so
treat it as a hint rather than a security boundary. Do not rely on it to sandbox
anything.

---

## SV015 — no unknown frontmatter keys

**info**

Unknown keys are ignored by most implementations. That silence is the problem:
you write `version: 2`, and three months later wonder why nothing changed.

If the value is meant for your own tooling, put it under `metadata`.

---

## SV016 — the body is not empty

**error**

The body is what the agent reads after activation. An empty body means the skill
wins the match and then has nothing to say — worse than not loading at all,
because it is harder to notice.

---

## SV017 — the body stays under 500 lines

**warning**

The specification recommends keeping `SKILL.md` under 500 lines and moving
detail into `references/`, which the agent reads only when it needs them.

The whole body is loaded at once, so length is a context cost paid on every
activation. The recommendation exists because 500 lines is roughly where a
document stops being an instruction and starts being a manual.

---

## SV018 — the body has a Markdown heading

**info**

A single `#` title makes the skill skimmable and makes diffs legible. Nothing
breaks without it. Everything is slightly worse.

---

## SV019 — references are relative, not absolute

**warning**

An absolute path works on exactly one machine. Skills get copied, vendored into
other repositories, and installed into shared directories.

```markdown
<!-- bad -->
See [the guide](/etc/skill-guide.md).

<!-- good -->
See [the guide](references/guide.md).
```

---

## SV020 — references are one level deep

**warning**

The specification recommends keeping file references one level from `SKILL.md`.
Deeper chains are hard for the agent to follow and hard for you to keep valid:
one rename in the middle and every path below it breaks silently.

---

## SV021 — referenced files exist

**error**

A broken link sends the agent into a dead end, and it will usually paper over
the failure rather than report it. This rule catches paths that no longer
resolve on disk.

This is the rule most likely to fire on a skill that was moved rather than
edited. Fixing it is almost always worth it.

---

## SV022 — every script in `scripts/` is mentioned

**warning**

A script the instructions never reference is either dead weight or a sign that
the skill was written in two passes and never reconciled. Both are worth
knowing about.

The check is deliberately loose: the filename appearing anywhere in the body
counts as a reference.