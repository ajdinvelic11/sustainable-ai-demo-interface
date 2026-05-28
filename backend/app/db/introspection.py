from functools import lru_cache

from psycopg import Connection


@lru_cache(maxsize=256)
def _cache_key(schema: str, table: str) -> tuple[str, str]:
    return schema, table


def table_exists(conn: Connection, schema: str, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_name = %s
            ) AS exists
            """,
            (schema, table),
        )
        return bool(cur.fetchone()["exists"])


def get_columns(conn: Connection, schema: str, table: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
            """,
            (schema, table),
        )
        return {row["column_name"] for row in cur.fetchall()}


def first_existing(columns: set[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None
