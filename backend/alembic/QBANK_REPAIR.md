# Historical QBank migration repair

`0003_placement_qbank` and `0007_placement_qbank` are parallel ancestors of
`0015_merge_vocabulary_fixed_bank`. Their table definitions are identical. Commit
`73c1efd` guarded both creates; merge `fbf5d6e` removed the guard from `0003`.
Consequently a full replay that visited `0007` first failed at `0003`.

Both revisions now load `qbank_compat_v1.py` relative to their own files. The helper
is part of the migration distribution, not an application-model import or an
additional revision. Always ship the whole Alembic directory. Keep this v1 schema
contract frozen; later schema changes require new revisions. Revision identities,
parents, merges, and the final head are unchanged.

## Upgrade and drift behavior

If absent, create the original 28-column table in `public`, with its original
constraints and six indexes. If present, inspect PostgreSQL catalogs without
writing rows, recreating indexes, or advancing the ID sequence. Validate exact
column names, types/schemas, nullability, lengths, defaults, public CEFR enum,
owned ID sequence, PK, unique constraint, both FKs/actions, and index semantics.
Compatible SERIAL or BY DEFAULT integer identity is accepted. Drift produces a
diagnostic identifying the differing property; it is never silently corrected.
Additional column/constraint drift is rejected. Non-conflicting additional
nonunique indexes do not change the required contract.

## Downgrade boundary

Both QBank downgrades raise before any destructive operation. Neither revision
owns the table exclusively, so dropping it can break the surviving branch. A
rollback crossing these revisions requires a separately reviewed recovery plan.
It is intentionally not a silent no-op or an automatic drop. Already-applied
revisions do not rerun validation; audit deployed schema before production replay.

## Validation

From `backend`, using the existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -B tests\test_qbank_migrations.py
.\.venv\Scripts\python.exe -B tests\run_qbank_migrations.py
```

The first command runs static graph/portability tests and explicitly skips DB
tests without disposable settings. The current second-command runner uses the
existing local PostgreSQL 16.14 server on the loopback interface. It obtains the
local PostgreSQL credentials through the Windows `pgpass.conf` mechanism, refuses
non-loopback servers, creates only uniquely named disposable test databases, and
deletes those databases after the suite. It does not load repository dotenv files
or expose the contents of `pgpass.conf`.

A Docker-based PostgreSQL 17.6 runner was originally intended, but Docker and a
PostgreSQL 17.6 container are not the environment used by the current runner.
Supabase PostgreSQL 17.6 is the deployment target, not the QBank regression-test
environment. Therefore these regression results must not be described as Supabase
validation unless a separate Supabase validation is explicitly performed and
recorded. No fallback from the local runner to Supabase is permitted.

Database tests copy only application code, migrations, and `alembic.ini` to an
isolated temporary directory without `.env` files. Child processes receive only
OS essentials, temporary DB URLs and a temporary JWT secret. They run real
Alembic CLI commands, never `create_all()` or stamping. Each test database has a
generated `edumind_qbank_*_test` name and is deleted after the suite.

Tests cover zero-to-head, either historical QBank branch first, both revision
identities, repeat-head, row/sequence/index preservation, real downgrade refusal,
and controlled schema drift against both revisions. Expected head schema is 127
product tables plus `alembic_version`, including 56 Language-domain tables.
QBank ORM parity must be exact; other ORM differences are reported without
changing models. No result from static tests alone authorizes a Supabase retry.
