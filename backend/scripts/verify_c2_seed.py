"""Quick check for Phase C2 seed counts."""
from sqlalchemy import create_engine, text

from app.core.config import get_settings

engine = create_engine(get_settings().DATABASE_URL_SYNC)
with engine.connect() as conn:
    rev = conn.execute(text("select version_num from alembic_version")).scalar()
    c2 = conn.execute(
        text(
            "select count(*) from language_content_items "
            "where body_json->>'seed_key' like 'c2_%'"
        )
    ).scalar()
    vocab = conn.execute(
        text(
            "select count(*) from language_content_items where content_type='vocabulary'"
        )
    ).scalar()
    writing = conn.execute(
        text(
            "select count(*) from language_content_items where content_type='writing_prompt'"
        )
    ).scalar()
    speaking = conn.execute(
        text(
            "select count(*) from language_content_items where content_type='speaking_prompt'"
        )
    ).scalar()
    print(f"revision={rev}")
    print(f"c2_seed={c2} vocabulary={vocab} writing={writing} speaking={speaking}")
    rows = conn.execute(
        text(
            "select level, count(*) from language_content_items "
            "where content_type='vocabulary' group by level order by level"
        )
    ).fetchall()
    for level, cnt in rows:
        print(f"  vocab {level}: {cnt}")
