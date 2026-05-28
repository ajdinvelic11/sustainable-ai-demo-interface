from __future__ import annotations

import logging
from pathlib import Path

from app.config import get_settings
from app.db import Database
from app.utils.logging import configure_logging

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    settings = get_settings()
    db = Database(settings)
    db.open()
    sql_dir = Path(__file__).resolve().parents[2] / "sql"
    files = sorted(sql_dir.glob("*.sql"))
    if not files:
        raise RuntimeError(f"No SQL migration files found in {sql_dir}")
    with db.connection() as conn:
        with conn.transaction():
            for file_path in files:
                logger.info("running_migration", extra={"_file": str(file_path)})
                conn.execute(file_path.read_text(encoding="utf-8"))
    db.close()
    logger.info("migrations_completed", extra={"_count": len(files)})


if __name__ == "__main__":
    configure_logging()
    run_migrations()

