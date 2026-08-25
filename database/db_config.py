"""
Single place that decides which database engine the app talks to.

- Default (zero setup): local SQLite file at data/incubator.db
- Production: set the DATABASE_URL env var to a MySQL DSN, e.g.
      DATABASE_URL=mysql+pymysql://user:pass@host:3306/incubator
  and install `pymysql` + `sqlalchemy` (both in requirements.txt).
  Every module in this project reads/writes through get_connection() /
  get_engine(), so switching engines never touches app or analytics code.
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_PATH = os.path.join(BASE_DIR, "data", "incubator.db")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


def get_connection():
    """
    Returns a DB-API connection.
    - If DATABASE_URL is set to a MySQL DSN, uses SQLAlchemy + pymysql.
    - Otherwise falls back to the bundled SQLite file (no setup required).
    """
    if DATABASE_URL and DATABASE_URL.startswith("mysql"):
        from sqlalchemy import create_engine
        engine = create_engine(DATABASE_URL)
        return engine.connect()
    return sqlite3.connect(SQLITE_PATH)


def is_mysql():
    return bool(DATABASE_URL) and DATABASE_URL.startswith("mysql")
