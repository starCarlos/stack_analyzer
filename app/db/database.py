from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from app.db.schema import NEWS_TABLES, TRACKING_TABLES


def _data_dir() -> Path:
    path = Path(os.getenv("DATA_DIR", "output"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def tracking_db_path() -> Path:
    return _data_dir() / "tracking.db"


def news_db_path() -> Path:
    return _data_dir() / "news.db"


def get_tracking_conn() -> sqlite3.Connection:
    return sqlite3.connect(tracking_db_path())


def get_news_conn() -> sqlite3.Connection:
    return sqlite3.connect(news_db_path())


def ensure_tables() -> None:
    with get_tracking_conn() as conn:
        for ddl in TRACKING_TABLES.values():
            conn.execute(ddl)
        conn.commit()
    with get_news_conn() as conn:
        for ddl in NEWS_TABLES.values():
            conn.execute(ddl)
        conn.commit()
