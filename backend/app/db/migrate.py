from pathlib import Path

from psycopg import sql

from app.db.session import db_connection, init_pool


SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def run_migrations() -> None:
    init_pool()
    files = sorted(SQL_DIR.glob("*.sql"))
    with db_connection() as conn:
        with conn.cursor() as cur:
            for file in files:
                cur.execute(file.read_text(encoding="utf-8"))
        conn.commit()


if __name__ == "__main__":
    run_migrations()
    print("Migrations applied.")
