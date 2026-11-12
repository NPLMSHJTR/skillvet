# Field notes: what OpenAI's own skills do

**Snapshot date: 2026-11-12.**

I measured the eleven skills under `.codex/skills/` in the Codex repository — the
ones the Codex team used to review their own code — and ran `skillvet` against
them. This document records what the numbers say and what I think they mean.

A note on provenance, because it matters here: **the directory no longer exists
upstream.** `openai/codex` returns 404 for `.codex/` as of the measurement date.
The copy these notes are based on is the historical snapshot preserved in
`NPLMSHJTR/codex`, which was forked on 2026-08-21 and is 3,819 commits behind.
So this is not a description of current OpenAI practice. It is a description of
one coherent set of skills, captured at a point in time, from the team that
wrote the specification the rest of us are working from.

That makes it more useful as evidence, not less: it is a real, working,
internally-consistent example, not a marketing artefact.

---

## The measurements

| directory | `name` | description length | bytes | body lines | body words |
| --- | --- | ---: | ---: | ---: | ---: |
| `code-review-breaking-changes` | `code-breaking-changes` | 16 | 336 | 8 | 38 |
| `code-review-change-size` | `code-review-change-size` | 32 | 478 | 6 | 63 |
| `test-tui` | `test-tui` | 41 | 545 | 10 | 73 |
| `code-review-testing` | `code-review-testing` | 23 | 618 | 10 | 85 |
| `code-review` | `code-review` | 41 | 666 | 10 | 92 |
| `code-review-context` | `code-review-context` | 21 | 673 | 9 | 98 |
| `path-types` | `path-types` | 153 | 2467 | 39 | 336 |
| `update-v8-version` | `update-v8-version` | 312 | 3450 | 68 | 416 |
| `remote-tests` | `remote-tests` | 54 | 3473 | 102 | 439 |
| `codex-pr-body` | `codex-pr-body` | 55 | 4508 | 57 | 734 |
| `babysit-pr` | `babysit-pr` | 514 | 17084 | 219 | 2502 |

Summary statistics:

- **Median size: 673 bytes.** Median body length: 10 lines.
- **Median description: 41 characters.** Longest: 514. Six of eleven are under
  60 characters.
- **3 of 11** descriptions contain a recognisable trigger phrase.
- **1 of 11** has a `name` that disagrees with its directory.
- Every file uses only `name` and `description` in the frontmatter. No `license`,
  no `metadata`, no `version`.
- The distribution is steeply skewed: the median file is 673 bytes, the largest
  is 17 KB, a factor of 25.

---

## Finding 1: they write much smaller than the community does

673 bytes is about 100 words. That is shorter than most README sections, shorter
than most prompts people paste into a chat window, and roughly a fortieth the
size of a typical "comprehensive" skill published today.

Two of the six `code-review-*` skills are under 350 bytes — small enough to read
in fifteen seconds:

```markdown
---
name: code-breaking-changes
description: Breaking changes
---

Search for breaking changes in external integration surfaces:
- app-server APIs
- CLI parameters
- configuration loading
- resuming sessions from existing rollouts

Do not stop after finding one issue; analyze all possible ways breaking changes can happen.
```

That is the entire skill. Thirty-eight words. It works because of what it leaves
out: no examples, no output format, no persona, no explanation of why breaking
changes matter. The audience is a competent reviewer — a model acting as one —
and the skill supplies only the part the reviewer would not think of unprompted.

**The design principle is subtraction.** A skill is not a prompt. It is the delta
between what a capable agent does by default and what you need it to do here.

---

## Finding 2: the small ones are rules, the big one is a loop

The size spread is not noise. Sorting the files by size reveals two distinct
categories with nothing in between:

**Under 700 bytes — constraint skills.** `code-review-*`, `test-tui`. Each states
one rule and stops. `code-review-change-size` is representative: *"Unless the
change is mechanical the total number of changed lines should not exceed 800
lines. For complex logic changes the size should be under 500 lines."* Six lines
of body. One number, one exception, one instruction about what to do when the
rule is violated.

**Over 2400 bytes — procedure skills.** `path-types`, `update-v8-version`,
`remote-tests`, `codex-pr-body`, `babysit-pr`. These describe sequences:
commands to run, conditions to check, orderings that matter.

`babysit-pr` at 17 KB is the outlier and it is instructive. It is not a rule. It
is a 219-line state machine for supervising a pull request over hours — polling
checks, interpreting failures, deciding when to retry versus escalate. It is big
because the thing it models is genuinely big.

**The lesson is not "write short skills".** It is: *constraints are cheap and
procedures are expensive, so do not spend procedure-sized text on a constraint.*
A 200-line skill that says "check for breaking changes" has buried one rule in
199 lines of noise, and the model will lose the rule.

---

## Finding 3: five skills, five dimensions — the orchestration pattern

`code-review` is 666 bytes and contains almost no review criteria at all. Its
entire job is dispatch:

```markdown
Use subagents to review code using all code-review-* skills other than this
orchestrator. One subagent per skill. Pass full skill path to subagents. Use
xhigh reasoning.

You must return every single issue from every subagent. You can return an
unlimited number of findings.
Use raw Markdown to report findings.
Number findings for ease of reference.
Each finding must include a specific file path and line number.
```

Read what that does. It splits review into four independent dimensions
(breaking changes, change size, testing, context design), gives each its own
subagent, and then constrains only the *output*: every issue, numbered, with a
file and line, no cap on count.

Why this beats one long review checklist:

- **Attention is not shared.** A reviewer told to check four things at once
  checks the easiest one thoroughly and the others shallowly. Four reviewers
  told to check one thing each do not have that option.
- **Each dimension can be tuned independently.** `code-review-change-size` holds
  a number (800 lines). Changing that number does not touch the breaking-change
  logic.
- **Failure is local.** If the testing reviewer produces noise, you rewrite 618
  bytes, not a monolith.

The cost is coordination, and the orchestrator's output contract is what pays
for it: without "every issue, numbered, with file and line", four subagents
produce four incompatible reports.

---

## Finding 4: the one skill that is mostly constraints

`code-review-context` is 673 bytes and every sentence in it is a prohibition or
a hard cap:

```markdown
1. No history rewrite - the context must be built up incrementally.
2. Avoid frequent changes to context that cause cache misses.
3. No unbounded items - everything injected in the model context must have a
   bounded size and a hard cap.
4. No items larger than 10K tokens.
5. Highlight new individual items that can cross >1k tokens as P0.
6. All injected fragments must be defined as structs in `core/context` and
   implement ContextualUserFragment trait
```

Six rules, and five of the six are negative. This is the most transferable
document in the set, because it is not about code review at all — it is about
designing the context window, which is the constraint every agent author runs
into and almost nobody writes down.

Two observations worth carrying into your own skills:

- **Numbers, not adjectives.** "Bounded" is a wish. "10K tokens" is checkable.
  "Avoid frequent changes" is vague; pairing it with the reason (cache misses)
  makes it actionable.
- **The reason is attached.** Each rule says what breaks, not just what to do.
  A model that knows *why* generalises to the case you did not anticipate. A
  model that knows only *what* does not.

---

## Finding 5: they do not write for discovery, and that is a trade-off

This is the finding that most directly contradicts current community advice, so
it deserves care.

Six of eleven descriptions are under 60 characters. Nine of eleven contain no
recognisable trigger phrase. `code-review-breaking-changes` says only "Breaking
changes". `code-review-context` says "Model visible context".

By the rules `skillvet` enforces, most of this set would be flagged — and by the
letter of the specification's advice ("describe both what the skill does and
when to use it"), it is under-specified.

The explanation is structural: **these skills are never discovered.** They are
dispatched. `code-review` names its children explicitly and passes their paths
to subagents. Nothing has to match on a description, because nothing is
searching.

So the short descriptions are correct *for this architecture*. They would be
wrong for a public skill directory where forty skills compete for a match.

The transferable rule is conditional:

> Write a trigger-rich description **if** the skill must win a match against
> siblings. Write a terse label **if** a parent skill dispatches to it by name.

`skillvet` cannot tell these apart, which is why SV009 and SV011 are warnings and
never errors. A linter that fails a build over a guess is a linter people
uninstall.

---

## Finding 6: the frontmatter is minimal

Every one of the eleven uses exactly two keys: `name` and `description`. Not one
sets `license`, `metadata`, `version`, or `allowed-tools`. Six of the eleven are
under 700 bytes total, frontmatter included.

The frontmatter exists to answer one question — should this load? — and the team
treated it as a place for exactly that answer and nothing else. Authorship,
versioning and provenance live in git, where they are maintained automatically
and cannot drift.

This is worth copying. A `version:` field in `SKILL.md` is a field that will be
wrong within a month.

---

## What I would take from this

| practice | adopt it? | caveat |
| --- | --- | --- |
| Keep constraint skills under ~1 KB | yes | procedures legitimately need more |
| Attach the reason to every rule | yes | costs a clause, buys generalisation |
| Split review into independent dimensions | yes | needs an output contract to work |
| Put numbers on every soft constraint | yes | "bounded" is not a constraint |
| Terse descriptions | **only** for dispatched skills | fails in a public directory |
| Two-key frontmatter | yes | add `license` if you redistribute |
| No `version` field | yes | let git carry it |

And one anti-pattern, observed rather than recommended: `code-review-breaking-changes`
has a `name` that does not match its directory. Even a team this disciplined
shipped a mismatch. That is the argument for putting this check in CI rather
than in a style guide.

---

## Reproducing this

The measurement is not a one-time snapshot you have to trust. Clone the fork,
point the tool at it, and get the same numbers:

```bash
git clone --depth 1 https://github.com/NPLMSHJTR/codex
skillvet codex/.codex/skills --no-color
```

The sizes in the table above come from `wc -c` on each `SKILL.md`. Body line and
word counts exclude the frontmatter block. Description lengths are the raw
string length after stripping quotes.

## Sources

"Specification." *Agent Skills*, agentskills.io/specification. Accessed 12 Nov. 2026.

"openai/codex." *GitHub*, github.com/openai/codex. Repository metadata retrieved
via the GitHub REST API, 12 Nov. 2026.

"Codex CLI." *GitHub*, github.com/openai/codex. Accessed 12 Nov. 2026.

Skill files: `.codex/skills/*/SKILL.md`, retrieved from
`NPLMSHJTR/codex` at commit state of 21 Aug. 2026. Licensed Apache-2.0.