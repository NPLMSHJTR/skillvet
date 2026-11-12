# Commit conventions

The grouping rules used by `scripts/group.py`, written down so a changelog can be
reviewed without reading the script.

## Parsing

A commit subject is treated as Conventional Commits if it matches:

```
type(scope)!: subject
type(scope): subject
type: subject
```

- `type` — one or more letters, case-insensitive
- `scope` — optional, anything except a closing parenthesis
- `!` — optional, immediately before the colon, marks a breaking change
- `subject` — the rest of the line

Anything else is classified as conventional: false and grouped under `Other`.
A commit whose subject is `Updated stuff` is not guessed at.

## Type to group mapping

| type | group |
| --- | --- |
| `feat`, `feature`, `add` | Added |
| `fix`, `bugfix`, `hotfix` | Fixed |
| `refactor`, `perf`, `style`, `docs` | Changed |
| `revert`, `remove`, `deprecate` | Removed |
| `build`, `ci`, `chore`, `test` | Other |
| anything unrecognised | Other |

`docs` and `style` sit in Changed rather than Other because they alter what a
user sees in the repository, even though they do not alter behaviour. If your
project treats them as noise, filter them out after grouping rather than
changing the mapping here — the mapping is deliberately conservative so that
nothing is hidden by default.

## Breaking-change detection

A commit is breaking if **either** condition holds:

1. the subject has `!` before the colon (`feat(api)!: drop v1 endpoints`), or
2. the commit body contains `BREAKING CHANGE` in any casing.

Nothing else counts. In particular:

- the word "breaking" appearing in the subject is **not** enough
- a large diff is **not** enough
- a change to a file named `api.py` is **not** enough

The script cannot see the diff, only the message, so it cannot judge whether a
change actually breaks an interface. If the message does not say so, the change
is not flagged — and that gap is real. The skill instructs the agent to mark
interface-touching changes as breaking by reading the diff itself, because the
script will not.

## Reliability signal

The output includes `conventional_ratio`, the share of commits that parsed as
Conventional Commits. Below 0.5 the grouping is reported as unreliable and the
`note` field says to prefer a flat list.

This exists because grouped output from unconventionally-named commits looks
authoritative while being arbitrary: `wip`, `fix`, `fix again` and `address
review` all land in `Other`, and a reader has no way to know the `Fixed` section
is empty because nothing was fixed rather than because nobody used the prefix.

## What the script does not do

- It does not read diffs. It cannot detect a breaking change the message omits.
- It does not resolve merge commits specially; a merge subject like
  `Merge pull request #42 from ...` lands in `Other`.
- It does not fetch. The range must already exist locally.
- It does not write to `CHANGELOG.md`. Formatting is the agent's job, because
  the shape of a good changelog depends on the project.