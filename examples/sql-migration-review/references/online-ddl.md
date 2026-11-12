# Online DDL notes

Which schema changes are safe while a table is serving traffic. Kept narrow on
purpose: only the operations a review is likely to see.

## PostgreSQL

### Adding a column

| operation | lock | safe online |
| --- | --- | --- |
| `ADD COLUMN c int` | brief `ACCESS EXCLUSIVE` | yes |
| `ADD COLUMN c int DEFAULT 0` | brief `ACCESS EXCLUSIVE` in 11+ | yes on 11+ |
| `ADD COLUMN c int DEFAULT 0` | full rewrite before 11 | no before 11 |
| `ADD COLUMN c int NOT NULL` | fails on non-empty table without default | no |
| `ADD COLUMN c int NOT NULL DEFAULT 0` | brief lock on 11+ | yes on 11+ |

The version 11 change is the one worth remembering: a constant default is now
stored in the catalog rather than written to every row. A volatile default such
as `now()` still rewrites.

### Indexes

| operation | blocks writes | safe online |
| --- | --- | --- |
| `CREATE INDEX` | yes, for the build | no |
| `CREATE INDEX CONCURRENTLY` | no | yes |
| `DROP INDEX` | yes | no |
| `DROP INDEX CONCURRENTLY` | no | yes |

`CREATE INDEX CONCURRENTLY` cannot run inside a transaction block. If your
migration tool wraps every migration in a transaction, it will fail — and the
failure leaves an invalid index behind that has to be dropped before retrying.

### Type changes

`ALTER COLUMN ... TYPE` rewrites the table unless the change is binary-coherent
(`varchar(50)` to `varchar(100)`, for example). A rewrite holds an exclusive lock
for its duration. There is no online form of this in core PostgreSQL.

### Constraints

| operation | note |
| --- | --- |
| `ADD CONSTRAINT ... FOREIGN KEY` | takes a lock on both tables; validate separately with `NOT VALID` then `VALIDATE CONSTRAINT` |
| `ADD CONSTRAINT ... CHECK` | same pattern: `NOT VALID`, then `VALIDATE` |
| `SET NOT NULL` | full scan unless a matching check constraint already exists |

The `NOT VALID` then `VALIDATE` pattern is the standard way to add a constraint
without blocking writes. It is two migrations, not one.

## MySQL (InnoDB)

`ALTER TABLE` in MySQL 8 supports `ALGORITHM=INSTANT`, `INPLACE` and `COPY`.
Specifying the algorithm turns a silent table rebuild into an error, which is
usually what you want in a review:

```sql
ALTER TABLE t ADD COLUMN c INT, ALGORITHM=INSTANT;
```

If the operation cannot be done instantly, the statement fails instead of
quietly rebuilding a million-row table. Adding a column at the end of the table
is instant in 8.0; adding it in the middle is not. Dropping a column is instant.
Changing a column type is almost never instant.

`CREATE INDEX` in MySQL 8 is online by default for InnoDB, with a brief metadata
lock at the start and end. `LOCK=NONE` makes the requirement explicit.

## SQLite

SQLite has no online DDL to speak of. `ALTER TABLE` supports only rename and add
column. Everything else is the twelve-step procedure: create a new table, copy,
drop, rename. On a live database this means downtime or a shadow table.

If a migration is written for SQLite and deployed to SQLite in production, that
is worth flagging in the review regardless of what the migration says.

## What a review should not claim

- **"This will lock the table."** Say which lock, and for how long, or say you do
  not know. "Locks the table" is true of nearly every DDL statement and therefore
  says nothing.
- **"Add an index."** Say which columns, in which order, and why that order. An
  index on the wrong column order does not help.
- **"This is safe."** Safe depends on table size, write rate, and replication
  lag, none of which the review can see. Say what the statement does and let the
  person who knows the table decide.