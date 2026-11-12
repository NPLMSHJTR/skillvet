---
name: sql-migration-review
description: Reviews a SQL migration for reversible changes, locking risk, and missing indexes before it reaches production. Use when the user shares a migration file or asks whether a schema change is safe to deploy.
license: MIT
---

# SQL migration review

Review the migration, not the schema it produces. The question is what happens to
a live table while this runs.

## Check in this order

Stop at the first blocking issue and report it alone. A review that lists twelve
problems when one of them will take the database down is a review nobody acts
on.

1. **Is it reversible?** Every `ALTER` and `DROP` should have a matching `down`
   migration. If the project does not use down migrations, the migration must be
   additive only.
2. **Does it lock?** On PostgreSQL, `ALTER TABLE ... ADD COLUMN ... DEFAULT` takes
   an exclusive lock before version 11 and is safe after. `CREATE INDEX` without
   `CONCURRENTLY` blocks writes for the duration of the build. On MySQL, most
   `ALTER TABLE` operations rebuild the table.
3. **Does it backfill?** Adding a `NOT NULL` column to a table with rows requires
   either a default or a backfill. A backfill inside the migration is a long
   transaction and should be split out.
4. **Is there an index for the new query?** A foreign key column with no index
   turns every join into a sequential scan.
5. **Is a column being dropped that code still reads?** Dropping a column is a
   two-deploy operation: stop reading, then drop.

## Report format

One paragraph of verdict, then the single blocking issue with the line that
causes it, then a short list of non-blocking notes.

## Rules

- Quote the exact line. Never describe a problem in the abstract.
- State the database engine you assumed, and ask if it was not given. Locking
  behaviour is not portable between PostgreSQL, MySQL and SQLite.
- Do not run the migration. Do not connect to a database. This skill reads files
  and reasons about them.
- If the migration is empty, or only touches tables not mentioned elsewhere in
  the repository, say that and stop. Manufacturing a finding to look thorough is
  worse than reporting nothing.

## Reference

Engine-specific locking notes, and the operations that are safe to run online,
are in [references/online-ddl.md](references/online-ddl.md).