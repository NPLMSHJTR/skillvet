---
name: changelog-from-tags
description: Generates release notes from git history between two tags, grouped by commit type. Use when the user asks for a changelog, release notes, or a summary of what changed since a version.
license: MIT
---

# Changelog from tags

Turn a range of commits into a changelog section that a human can read.

## Steps

1. Find the range. If the user gave two tags, use them:

   ```bash
   git log --oneline v1.2.0..v1.3.0
   ```

   If they gave none, use the latest tag to `HEAD`, and say which tag you
   picked. If there are no tags at all, fall back to the last 50 commits and
   say so in the output.

2. Group the commits with the helper script:

   ```bash
   python scripts/group.py v1.2.0..v1.3.0
   ```

3. Write the section in this order, skipping empty groups:
   `Breaking`, `Added`, `Changed`, `Fixed`, `Removed`, `Other`.

4. Date the section with the tag's date, not today's:

   ```bash
   git log -1 --format=%cs v1.3.0
   ```

## Rules

- Never invent a description. If a commit message is `wip` or `fix`, either
  quote it verbatim or leave it out and note the count of omitted commits.
- Do not merge two commits into one line unless one is clearly a fixup of the
  other, and say which.
- Mark a commit as breaking only if it says so (`BREAKING CHANGE`, `!:` after
  the type) or the diff touches a public interface. Do not guess from the
  wording.
- Prepend the new section. Never rewrite history in `CHANGELOG.md`.

## Commit message convention

The grouping assumes Conventional Commits (`feat:`, `fix:`, `chore:` and so on).
If fewer than half the commits in the range match, say so and output one flat
list instead of pretending the groups are meaningful.

## Reference

The full type-to-group mapping and the breaking-change detection rules are in
[references/commit-conventions.md](references/commit-conventions.md).