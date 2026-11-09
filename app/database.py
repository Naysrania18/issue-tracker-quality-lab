"""SQLite access. Plain sqlite3 keeps the SQL visible, which helps when testing data integrity."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('reporter','engineer','qa')),
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    token TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES components(id),
    UNIQUE (name, parent_id)
);
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    steps_to_reproduce TEXT NOT NULL DEFAULT '',
    expected_result TEXT NOT NULL DEFAULT '',
    actual_result TEXT NOT NULL DEFAULT '',
    component_id INTEGER NOT NULL REFERENCES components(id),
    priority TEXT NOT NULL CHECK (priority IN ('P1','P2','P3','P4')),
    assignee_id INTEGER REFERENCES users(id),
    reporter_id INTEGER NOT NULL REFERENCES users(id),
    state TEXT NOT NULL DEFAULT 'Analyze',
    duplicate_of INTEGER REFERENCES issues(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL REFERENCES issues(id),
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL REFERENCES issues(id),
    author TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    component_id INTEGER NOT NULL REFERENCES components(id),
    steps TEXT NOT NULL DEFAULT '',
    expected TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS suites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS suite_cases (
    suite_id INTEGER NOT NULL REFERENCES suites(id),
    case_id INTEGER NOT NULL REFERENCES test_cases(id),
    PRIMARY KEY (suite_id, case_id)
);
CREATE TABLE IF NOT EXISTS test_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    suite_id INTEGER NOT NULL REFERENCES suites(id),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running'
);
CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES test_runs(id),
    case_id INTEGER NOT NULL REFERENCES test_cases(id),
    status TEXT NOT NULL CHECK (status IN ('passed','failed','skipped')),
    issue_id INTEGER REFERENCES issues(id),
    duration_ms INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def connect(path: str) -> sqlite3.Connection:
    # check_same_thread=False because FastAPI runs sync handlers in a thread pool.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: str) -> None:
    conn = connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
