"""
Creates data/incubator.db (SQLite) from the CSV seed files, using a schema
that mirrors schema_mysql.sql (adjusted only for SQLite's type affinities --
AUTO_INCREMENT -> AUTOINCREMENT, DECIMAL -> REAL/NUMERIC, TINYINT -> INTEGER).

Run:  python database/init_db.py
"""
import os
import sqlite3
import csv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "incubator.db")

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS startups (
    startup_id      INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    industry        TEXT NOT NULL,
    stage           TEXT NOT NULL,
    founded_date    TEXT NOT NULL,
    neighborhood    TEXT,
    founder_name    TEXT,
    employee_count  INTEGER DEFAULT 0,
    impact_score    REAL,
    active          INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS mentors (
    mentor_id        INTEGER PRIMARY KEY,
    name             TEXT NOT NULL,
    expertise        TEXT,
    years_experience INTEGER,
    avg_rating       REAL,
    mentor_type      TEXT,
    joined_date      TEXT
);

CREATE TABLE IF NOT EXISTS investors (
    investor_id     INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    investor_type   TEXT,
    focus_industry  TEXT,
    portfolio_size  INTEGER,
    joined_date     TEXT
);

CREATE TABLE IF NOT EXISTS events (
    event_id        INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    event_type      TEXT,
    event_date      TEXT,
    capacity        INTEGER,
    cost_usd        REAL
);

CREATE TABLE IF NOT EXISTS funding_rounds (
    funding_round_id INTEGER PRIMARY KEY,
    startup_id        INTEGER NOT NULL REFERENCES startups(startup_id) ON DELETE CASCADE,
    round_type        TEXT,
    amount_usd        REAL,
    round_date        TEXT
);

CREATE TABLE IF NOT EXISTS investments (
    investment_id       INTEGER PRIMARY KEY,
    funding_round_id     INTEGER NOT NULL REFERENCES funding_rounds(funding_round_id) ON DELETE CASCADE,
    investor_id           INTEGER NOT NULL REFERENCES investors(investor_id) ON DELETE CASCADE,
    participation_share   REAL
);

CREATE TABLE IF NOT EXISTS mentorship_sessions (
    session_id       INTEGER PRIMARY KEY,
    startup_id       INTEGER NOT NULL REFERENCES startups(startup_id) ON DELETE CASCADE,
    mentor_id        INTEGER NOT NULL REFERENCES mentors(mentor_id) ON DELETE CASCADE,
    session_date     TEXT,
    duration_minutes INTEGER,
    session_rating   REAL,
    topic            TEXT
);

CREATE TABLE IF NOT EXISTS event_participation (
    participation_id INTEGER PRIMARY KEY,
    event_id          INTEGER NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    attendee_type     TEXT NOT NULL,
    attendee_id       INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_funding_startup     ON funding_rounds(startup_id);
CREATE INDEX IF NOT EXISTS idx_invest_round        ON investments(funding_round_id);
CREATE INDEX IF NOT EXISTS idx_invest_investor     ON investments(investor_id);
CREATE INDEX IF NOT EXISTS idx_session_startup     ON mentorship_sessions(startup_id);
CREATE INDEX IF NOT EXISTS idx_session_mentor      ON mentorship_sessions(mentor_id);
CREATE INDEX IF NOT EXISTS idx_participation_event ON event_participation(event_id);
CREATE INDEX IF NOT EXISTS idx_startups_industry   ON startups(industry);
CREATE INDEX IF NOT EXISTS idx_startups_stage      ON startups(stage);
"""

TABLE_ORDER = [
    "startups", "mentors", "investors", "events",
    "funding_rounds", "investments", "mentorship_sessions", "event_participation",
]


def load_csv(cursor, table):
    csv_path = os.path.join(DATA_DIR, f"{table}.csv")
    if not os.path.exists(csv_path):
        print(f"  ! skipping {table} (no CSV found at {csv_path})")
        return
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        placeholders = ",".join(["?"] * len(header))
        rows = list(reader)
        cursor.executemany(
            f"INSERT INTO {table} ({','.join(header)}) VALUES ({placeholders})", rows
        )
    print(f"  loaded {len(rows):>5} rows -> {table}")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(DDL)
    print("Loading seed CSVs into SQLite ...")
    for table in TABLE_ORDER:
        load_csv(cur, table)
    conn.commit()
    conn.close()
    print(f"\nDatabase ready at {DB_PATH}")


if __name__ == "__main__":
    main()
