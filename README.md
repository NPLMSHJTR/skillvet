# skillvet

**A static checker for Agent Skills. It catches the mistakes that make a skill load but never fire.**

![version](https://img.shields.io/badge/version-0.1.0-blue)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)
![rules](https://img.shields.io/badge/rules-22-orange)
[![CI](https://github.com/NPLMSHJTR/skillvet/actions/workflows/ci.yml/badge.svg)](https://github.com/NPLMSHJTR/skillvet/actions/workflows/ci.yml)

A skill is a directory with a `SKILL.md`. The agent reads only `name` and
`description` when deciding whether to load it — everything else waits. That
makes the frontmatter the highest-leverage 200 characters in the whole system,
and it is also where almost every skill quietly fails.

`skillvet` checks a skill against the Agent Skills specification and against the
patterns that stop skills from triggering. It has 22 rules, no dependencies, and
exit codes designed for CI.

```console
$ skillvet skills/

W skills/pdf-tables/SKILL.md (pdf-tables) — 2 warnings
    warn SV009 `description` never says when the skill should be used
         Add an explicit trigger, for example "Use when the user asks to ...".
    warn SV011 `description` is only 24 characters
         Short descriptions tend to under-trigger.

P skills/changelog/SKILL.md
    no findings

2 skills checked · 1 with warnings · 1 clean
```

## What it caught on OpenAI's own skills

I ran it against the eleven skills in `openai/codex`'s `.codex/skills/`
directory, the ones the Codex team used to review their own repository. The
results are in [docs/field-notes.md](docs/field-notes.md), and one finding is
worth repeating here:

```
error SV006 `name` is `code-breaking-changes` but the directory is
            `code-review-breaking-changes`
```

The directory and the `name` field disagree. Under the specification the two
must match, and a mismatch is the kind of thing that silently breaks discovery.

Nine of the eleven descriptions also lack any trigger phrase, and the median
skill is 673 bytes. That is the opposite of how most published skills are
written. [docs/field-notes.md](docs/field-notes.md) works through why.

## Install

```bash
pipx install skillvet
```

Or run it without installing anything:

```bash
python -m pip install --user git+https://github.com/NPLMSHJTR/skillvet
```

Or clone and run from source, with no dependencies at all:

```bash
git clone https://github.com/NPLMSHJTR/skillvet
cd skillvet
python -m skillvet path/to/skills
```

PyYAML is optional. With it, frontmatter is parsed properly. Without it, a small
built-in parser handles the flat key/value shape that skills actually use.

## Use

```bash
skillvet                      # check the current directory, recursively
skillvet skills/              # check one tree
skillvet skills/pdf/SKILL.md  # check one file
skillvet --strict skills/     # let warnings fail the build
skillvet --format json        # machine-readable, for editors and dashboards
skillvet --no-info skills/    # hide style suggestions
```

Exit codes:

| code | meaning |
| --- | --- |
| `0` | everything passed |
| `1` | a finding at or above the failure threshold (`error`, or `warning` with `--strict`) |
| `2` | usage error, or no `SKILL.md` was found |

## In CI

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- run: pip install skillvet
- run: skillvet skills/ --strict
```

## The rules

Twenty-two rules across three severities. Full rationale, examples and the
before/after for each one is in [docs/rules.md](docs/rules.md).

| id | severity | what it checks |
| --- | --- | --- |
| SV001 | error | `name` is present and non-empty |
| SV002 | error | `name` is at most 64 characters |
| SV003 | error | `name` uses only `a-z`, `0-9` and single hyphens |
| SV006 | error | `name` equals the parent directory name |
| SV007 | error | `description` is present, non-empty, single-line |
| SV008 | error | `description` is at most 1024 characters |
| SV009 | warning | `description` states when to use the skill |
| SV010 | warning | `description` does not open with a vague phrase |
| SV011 | warning | `description` is not too short to match on |
| SV012 | error | `compatibility` is at most 500 characters |
| SV013 | error | `metadata` is a string-to-string mapping |
| SV014 | error | `allowed-tools` is a space-separated string |
| SV015 | info | no unknown frontmatter keys |
| SV016 | error | the body is not empty |
| SV017 | warning | the body stays under 500 lines |
| SV018 | info | the body has a Markdown heading |
| SV019 | warning | references are relative, not absolute |
| SV020 | warning | references are one level deep |
| SV021 | error | referenced files exist |
| SV022 | warning | every script in `scripts/` is mentioned |

The specification numbers behind these — 64 characters, 1024 characters, 500
lines — come from the [Agent Skills specification](https://agentskills.io/specification),
not from guesswork.

## Why the rules look like this

Three claims shape the rule set. Each is argued and sourced in
[docs/field-notes.md](docs/field-notes.md):

1. **The description is the entire decision surface.** It is loaded for every
   skill on every turn; the body is loaded only after a match. A skill whose
   description does not say *when* to fire is a skill that will not fire.
2. **Short beats long.** OpenAI's internal skills have a median size of 673
   bytes. The longest is 17 KB, and it is the one that coordinates a
   long-running review loop, not the one that encodes a rule.
3. **One skill, one job.** The five `code-review-*` skills each enforce a single
   constraint. Splitting a checklist into dimensions is what makes each finding
   specific enough to act on.

## Docs

| file | what is in it |
| --- | --- |
| [docs/rules.md](docs/rules.md) | every rule: why it exists, what breaks without it, bad vs good |
| [docs/anti-patterns.md](docs/anti-patterns.md) | twelve real failure modes, side by side |
| [docs/field-notes.md](docs/field-notes.md) | what OpenAI's own skills do, measured |

## Status

Version 0.1.0. The rule set and the CLI contract are stable. Rules are additive;
ids are never reused, so a suppression list will not rot.

CI runs the suite on Ubuntu, Windows and macOS across Python 3.9 and 3.13, plus
a job that installs with no third-party packages and asserts PyYAML really is
absent — because "zero dependencies" is a claim that silently stops being true.

Known gaps, stated plainly:

- Trigger detection is heuristic. It matches phrase patterns, so a skill that
  triggers correctly through wording I did not anticipate gets a false warning.
  `SV009` is a warning, never an error, for this reason.
- Only `SKILL.md` is checked. Plugin manifests and marketplace files are out of
  scope for now.
- Non-English descriptions are checked for Chinese trigger phrases; other
  languages are not recognised yet.
- The built-in fallback parser implements a subset of YAML: scalars, nested
  maps, block lists, block scalars and nulls. Anchors, aliases, multi-document
  files and flow style are rejected rather than guessed at.
  `tests/test_parser_equivalence.py` asserts the two parsers agree on sixteen
  input shapes.

Issues and rule proposals are welcome. If you have a skill that `skillvet`
misjudges, that is the most useful bug report you can send.

## License

MIT.