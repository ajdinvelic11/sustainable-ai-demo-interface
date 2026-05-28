from __future__ import annotations

import logging
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator

from psycopg import Connection, sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import Settings

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.pool: ConnectionPool[Any] | None = None

    def open(self) -> None:
        if self.pool is not None:
            return
        self.pool = ConnectionPool(
            conninfo=self.settings.database_dsn,
            min_size=self.settings.db_pool_min_size,
            max_size=self.settings.db_pool_max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        logger.info("database_pool_opened")

    def close(self) -> None:
        if self.pool is not None:
            self.pool.close()
            self.pool = None
            logger.info("database_pool_closed")

    @contextmanager
    def connection(self) -> Iterator[Connection[Any]]:
        if self.pool is None:
            self.open()
        assert self.pool is not None
        with self.pool.connection() as conn:
            yield conn

    def ping(self) -> bool:
        with self.connection() as conn:
            row = conn.execute("select 1 as ok").fetchone()
            return bool(row and row["ok"] == 1)

    def table_exists(self, schema_name: str, table_name: str) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                """
                select exists (
                    select 1
                    from information_schema.tables
                    where table_schema = %s and table_name = %s
                ) as exists
                """,
                (schema_name, table_name),
            ).fetchone()
            return bool(row and row["exists"])

    def relation_exists(self, schema_name: str, relation_name: str) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                """
                select exists (
                    select 1
                    from pg_catalog.pg_class c
                    join pg_catalog.pg_namespace n on n.oid = c.relnamespace
                    where n.nspname = %s and c.relname = %s and c.relkind in ('r', 'v', 'm')
                ) as exists
                """,
                (schema_name, relation_name),
            ).fetchone()
            return bool(row and row["exists"])

    @lru_cache(maxsize=256)
    def columns(self, schema_name: str, table_name: str) -> dict[str, dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                select column_name, data_type, udt_name, is_nullable, column_default
                from information_schema.columns
                where table_schema = %s and table_name = %s
                order by ordinal_position
                """,
                (schema_name, table_name),
            ).fetchall()
        return {row["column_name"]: dict(row) for row in rows}

    def clear_column_cache(self) -> None:
        self.columns.cache_clear()

    def first_existing_column(self, schema_name: str, table_name: str, candidates: list[str]) -> str | None:
        columns = self.columns(schema_name, table_name)
        return next((column for column in candidates if column in columns), None)

    def insert_dynamic(
        self,
        conn: Connection[Any],
        schema_name: str,
        table_name: str,
        values: dict[str, Any],
        returning_candidates: list[str] | None = None,
    ) -> dict[str, Any] | None:
        columns = self.columns(schema_name, table_name)
        filtered = {key: value for key, value in values.items() if key in columns and value is not None}
        if not filtered:
            raise ValueError(f"No compatible columns found for {schema_name}.{table_name}")

        identifiers = [sql.Identifier(name) for name in filtered]
        placeholders = [sql.Placeholder() for _ in filtered]
        returning_column = self.first_existing_column(schema_name, table_name, returning_candidates or [])

        query = sql.SQL("insert into {}.{} ({}) values ({})").format(
            sql.Identifier(schema_name),
            sql.Identifier(table_name),
            sql.SQL(", ").join(identifiers),
            sql.SQL(", ").join(placeholders),
        )
        if returning_column:
            query += sql.SQL(" returning {}").format(sql.Identifier(returning_column))
        cursor = conn.execute(query, tuple(filtered.values()))
        return cursor.fetchone() if returning_column else None

    def update_dynamic(
        self,
        conn: Connection[Any],
        schema_name: str,
        table_name: str,
        values: dict[str, Any],
        where_column: str,
        where_value: Any,
    ) -> int:
        columns = self.columns(schema_name, table_name)
        filtered = {key: value for key, value in values.items() if key in columns}
        if not filtered:
            return 0
        assignments = [
            sql.SQL("{} = {}").format(sql.Identifier(name), sql.Placeholder())
            for name in filtered
        ]
        query = sql.SQL("update {}.{} set {} where {} = {}").format(
            sql.Identifier(schema_name),
            sql.Identifier(table_name),
            sql.SQL(", ").join(assignments),
            sql.Identifier(where_column),
            sql.Placeholder(),
        )
        cursor = conn.execute(query, (*filtered.values(), where_value))
        return cursor.rowcount or 0

