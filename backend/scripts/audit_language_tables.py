import os

import psycopg2


def main() -> None:
    url = os.environ.get("DATABASE_URL_SYNC") or os.environ.get("DATABASE_URL")
    if not url:
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = os.environ.get("POSTGRES_PORT", "5432")
        user = os.environ.get("POSTGRES_USER", "postgres")
        pw = os.environ.get("POSTGRES_PASSWORD", "")
        db = os.environ.get("POSTGRES_DB", "eduspark")
        url = "postgresql://{u}:{p}@{h}:{pt}/{d}".format(u=user, p=pw, h=host, pt=port, d=db)

    conn = psycopg2.connect(url)
    cur = conn.cursor()

    cur.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'language_%' ORDER BY tablename"
    )
    rows = [r[0] for r in cur.fetchall()]
    print("language_tables", len(rows))
    for t in rows:
        print(t)

    cur.execute("SELECT version_num FROM alembic_version")
    print("alembic_version", cur.fetchone()[0])

    conn.close()


if __name__ == "__main__":
    main()
