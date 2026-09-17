"""Frozen PostgreSQL contract shared by the two historical QBank revisions.

Keep this file with the Alembic directory. It must not import application models.
Future schema evolution belongs in new revisions, not in this v1 contract.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

TABLE = "language_placement_question_bank_items"
QUALIFIED = "public." + TABLE
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
COLUMNS = {
    "id": ("int4", "NO", None),
    "language_id": ("int4", "NO", None),
    "skill": ("varchar", "NO", 32),
    "level": ("language_level", "NO", None),
    "boundary_low_level": ("language_level", "YES", None),
    "boundary_high_level": ("language_level", "YES", None),
    "subskill": ("varchar", "YES", 64),
    "question_type": ("varchar", "NO", 32),
    "prompt_text": ("text", "NO", None),
    "passage": ("text", "YES", None),
    "situation": ("text", "YES", None),
    "options_json": ("jsonb", "YES", None),
    "correct_index": ("int4", "YES", None),
    "explanation": ("text", "YES", None),
    "media_object_id": ("int4", "YES", None),
    "audio_meta_json": ("jsonb", "YES", None),
    "body_json": ("jsonb", "YES", None),
    "stable_key": ("varchar", "YES", 160),
    "source": ("varchar", "NO", 32),
    "is_verified": ("bool", "NO", None),
    "is_active": ("bool", "NO", None),
    "reviewer_note": ("text", "YES", None),
    "usage_count": ("int4", "NO", None),
    "correct_count": ("int4", "NO", None),
    "difficulty_estimate": ("float8", "YES", None),
    "discrimination_estimate": ("float8", "YES", None),
    "created_at": ("timestamptz", "NO", None),
    "updated_at": ("timestamptz", "NO", None),
}
DEFAULTS = {
    "question_type": {"'mcq'::character varying", "'mcq'::text", "'mcq'"},
    "source": {"'ai_generated'::character varying", "'ai_generated'::text", "'ai_generated'"},
    "is_verified": {"false"}, "is_active": {"true"},
    "usage_count": {"0"}, "correct_count": {"0"},
    "created_at": {"now()"}, "updated_at": {"now()"},
}
INDEXES = {
    "ix_lpq_bank_boundary": ["language_id", "skill", "boundary_low_level", "boundary_high_level", "is_verified", "is_active"],
    "ix_lpq_bank_lookup": ["language_id", "skill", "level", "is_verified", "is_active"],
    **{"ix_" + TABLE + "_" + col: [col] for col in ("language_id", "level", "skill", "subskill")},
}


def _fail(item, expected, actual):
    raise RuntimeError(f"QBank schema drift: {QUALIFIED}.{item}: expected {expected!r}; found {actual!r}. No automatic repair was attempted.")


def _equal(item, expected, actual):
    if actual != expected:
        _fail(item, expected, actual)


def validate(bind):
    """Read catalogs only; accepting an existing table must not advance sequences."""
    relation = bind.execute(sa.text("SELECT relkind FROM pg_class WHERE oid=to_regclass(:table)"), {"table": QUALIFIED}).scalar()
    _equal("relation kind", "r", relation)
    rows = bind.execute(sa.text("""
        SELECT column_name, udt_schema, udt_name, is_nullable,
               character_maximum_length, column_default, is_identity,
               identity_generation, is_generated
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=:table
    """), {"table": TABLE}).mappings().all()
    columns = {r["column_name"]: r for r in rows}
    _equal("column names", sorted(COLUMNS), sorted(columns))
    for name, definition in COLUMNS.items():
        row = columns[name]
        _equal(name + " type/nullability/length", definition,
               (row["udt_name"], row["is_nullable"], row["character_maximum_length"]))
        _equal(name + " type schema", "public" if definition[0] == "language_level" else "pg_catalog", row["udt_schema"])
        _equal(name + " generated expression", "NEVER", row["is_generated"])
        if name != "id":
            _equal(name + " identity", "NO", row["is_identity"])
            allowed = DEFAULTS.get(name, {None})
            if row["column_default"] not in allowed:
                _fail(name + " server default", sorted(str(x) for x in allowed), row["column_default"])
    labels = bind.execute(sa.text("""
        SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid
        JOIN pg_namespace n ON n.oid=t.typnamespace
        WHERE n.nspname='public' AND t.typname='language_level' ORDER BY e.enumsortorder
    """)).scalars().all()
    _equal("language_level labels", LEVELS, labels)

    sequence = bind.execute(sa.text("SELECT pg_get_serial_sequence(:table, 'id')"), {"table": QUALIFIED}).scalar()
    if not sequence:
        _fail("id generation", "owned SERIAL/IDENTITY sequence", None)
    if columns["id"]["is_identity"] == "YES":
        _equal("id identity generation", "BY DEFAULT", columns["id"]["identity_generation"])
        _equal("id identity default", None, columns["id"]["column_default"])
    else:
        expected = bind.execute(sa.text("SELECT format('nextval(%L::regclass)', CAST(:sequence AS regclass)::text)"), {"sequence": sequence}).scalar_one()
        _equal("id sequence default", expected, columns["id"]["column_default"])
    seq = bind.execute(sa.text("""
        SELECT seqtypid::regtype::text, seqstart, seqincrement, seqmin, seqmax, seqcycle
        FROM pg_sequence WHERE seqrelid=CAST(:sequence AS regclass)
    """), {"sequence": sequence}).one()
    _equal("id sequence configuration", ("integer", 1, 1, 1, 2147483647, False), tuple(seq))

    constraints = bind.execute(sa.text("""
        SELECT c.contype, c.convalidated, c.condeferrable, c.condeferred,
          ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(num, pos)
                JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.num ORDER BY k.pos) AS cols,
          n.nspname AS target_schema, r.relname AS target_table,
          ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(num, pos)
                JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.num ORDER BY k.pos) AS target_cols,
          c.confdeltype, c.confupdtype, c.confmatchtype
        FROM pg_constraint c LEFT JOIN pg_class r ON r.oid=c.confrelid
        LEFT JOIN pg_namespace n ON n.oid=r.relnamespace
        WHERE c.conrelid=to_regclass(:table)
    """), {"table": QUALIFIED}).mappings().all()
    actual = []
    for c in constraints:
        _equal("constraint " + str(c["cols"]) + " validated/nondeferrable", (True, False, False),
               (c["convalidated"], c["condeferrable"], c["condeferred"]))
        actual.append((c["contype"], tuple(c["cols"]), c["target_schema"], c["target_table"],
                       tuple(c["target_cols"]), c["confdeltype"], c["confupdtype"], c["confmatchtype"]))
    expected = [
        ("p", ("id",), None, None, (), " ", " ", " "),
        ("u", ("stable_key",), None, None, (), " ", " ", " "),
        ("f", ("language_id",), "public", "languages", ("id",), "c", "a", "s"),
        ("f", ("media_object_id",), "public", "media_objects", ("id",), "n", "a", "s"),
    ]
    _equal("PK/unique/FK definitions", sorted(expected), sorted(actual))
    indexes = bind.execute(sa.text("""
        SELECT r.relname, i.indisunique, i.indisprimary, i.indisvalid, i.indisready,
          i.indnullsnotdistinct, i.indnatts, i.indnkeyatts, i.indoption::smallint[] AS options,
          pg_get_expr(i.indexprs,i.indrelid) AS expressions,
          pg_get_expr(i.indpred,i.indrelid) AS predicate, am.amname,
          ARRAY(SELECT a.attname FROM unnest(i.indkey) WITH ORDINALITY k(num,pos)
                LEFT JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.num ORDER BY k.pos) AS cols,
          (SELECT bool_and(o.opcdefault) FROM unnest(i.indclass) oc(oid)
                JOIN pg_opclass o ON o.oid=oc.oid) AS default_opclasses,
          (SELECT bool_and(col.oid=a.attcollation)
                FROM unnest(i.indcollation) WITH ORDINALITY col(oid,pos)
                JOIN unnest(i.indkey) WITH ORDINALITY k(num,pos) ON k.pos=col.pos
                JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.num) AS column_collations
        FROM pg_index i JOIN pg_class r ON r.oid=i.indexrelid
        JOIN pg_am am ON am.oid=r.relam WHERE i.indrelid=to_regclass(:table)
    """), {"table": QUALIFIED}).mappings().all()
    by_name = {r["relname"]: r for r in indexes}
    for name, cols in INDEXES.items():
        if name not in by_name:
            _fail("index " + name, cols, "missing")
        row = by_name[name]
        _equal("index " + name + " definition",
               (cols, False, False, True, True, False, len(cols), len(cols), [0] * len(cols), None, None, "btree", True, True),
               (row["cols"], row["indisunique"], row["indisprimary"], row["indisvalid"], row["indisready"],
                row["indnullsnotdistinct"], row["indnatts"], row["indnkeyatts"], row["options"],
                row["expressions"], row["predicate"], row["amname"], row["default_opclasses"], row["column_collations"]))
    unique = [r for r in indexes if r["indisunique"]]
    _equal("unique index keys", [("id",), ("stable_key",)], sorted(tuple(r["cols"]) for r in unique))
    for row in unique:
        _equal("unique index " + row["relname"] + " semantics",
               (True, True, False, None, None, 1, 1, [0], "btree", True, True, row["cols"] == ["id"]),
               (row["indisvalid"], row["indisready"], row["indnullsnotdistinct"], row["predicate"], row["expressions"],
                row["indnatts"], row["indnkeyatts"], row["options"], row["amname"], row["default_opclasses"],
                row["column_collations"], row["indisprimary"]))


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("QBank compatibility requires live PostgreSQL catalog inspection.")
    if bind.execute(sa.text("SELECT to_regclass(:table)"), {"table": QUALIFIED}).scalar() is not None:
        validate(bind)
        return
    level = postgresql.ENUM(*LEVELS, name="language_level", schema="public", create_type=False)
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.Column("skill", sa.String(32), nullable=False),
        sa.Column("level", level, nullable=False),
        sa.Column("boundary_low_level", level, nullable=True),
        sa.Column("boundary_high_level", level, nullable=True),
        sa.Column("subskill", sa.String(64), nullable=True),
        sa.Column("question_type", sa.String(32), server_default="mcq", nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("passage", sa.Text(), nullable=True),
        sa.Column("situation", sa.Text(), nullable=True),
        sa.Column("options_json", postgresql.JSONB(), nullable=True),
        sa.Column("correct_index", sa.Integer(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("media_object_id", sa.Integer(), nullable=True),
        sa.Column("audio_meta_json", postgresql.JSONB(), nullable=True),
        sa.Column("body_json", postgresql.JSONB(), nullable=True),
        sa.Column("stable_key", sa.String(160), nullable=True),
        sa.Column("source", sa.String(32), server_default="ai_generated", nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("usage_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("correct_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("difficulty_estimate", sa.Float(), nullable=True),
        sa.Column("discrimination_estimate", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["language_id"], ["public.languages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_object_id"], ["public.media_objects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("stable_key"), schema="public",
    )
    for name, cols in INDEXES.items():
        op.create_index(name, TABLE, cols, schema="public")
    validate(bind)


def downgrade(revision):
    raise RuntimeError(
        f"Downgrade blocked at {revision}: {QUALIFIED} is shared by parallel "
        "0003_placement_qbank and 0007_placement_qbank history. Neither revision "
        "exclusively owns it. Use a separately reviewed recovery procedure; "
        "this downgrade performs no destructive action."
    )
