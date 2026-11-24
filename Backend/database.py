import sqlite3
from .config import DB_PATH

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def initialize():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT 'Guest', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS profiles(user_id TEXT PRIMARY KEY REFERENCES users(id), role_id TEXT, level_id TEXT, skill_ids TEXT, career_data TEXT);
        CREATE TABLE IF NOT EXISTS plan_items(id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), title TEXT, description TEXT, week INTEGER, completed INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS answers(id INTEGER PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), question_id TEXT, correct INTEGER, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS focus_sessions(id INTEGER PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), duration_seconds INTEGER, prompt_id TEXT, completed INTEGER, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS task_state(user_id TEXT NOT NULL REFERENCES users(id), task_id TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id,task_id));
        CREATE TABLE IF NOT EXISTS reviews(user_id TEXT NOT NULL REFERENCES users(id), review_id TEXT NOT NULL, started_at TEXT, PRIMARY KEY(user_id,review_id));
        CREATE TABLE IF NOT EXISTS readiness_snapshots(user_id TEXT NOT NULL REFERENCES users(id), snapshot_date TEXT NOT NULL, score INTEGER NOT NULL, PRIMARY KEY(user_id,snapshot_date));
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL, expires_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS user_activity(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL REFERENCES users(id), action TEXT NOT NULL, details TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_answers_user_created ON answers(user_id,created_at);
        CREATE INDEX IF NOT EXISTS idx_focus_user_created ON focus_sessions(user_id,created_at);
        CREATE INDEX IF NOT EXISTS idx_activity_user_created ON user_activity(user_id,created_at);
        """)
        # Add account columns to databases created by earlier backend versions.
        for column, definition in (("username", "TEXT"), ("password_hash", "TEXT"), ("password_salt", "TEXT"), ("last_login_at", "TEXT")):
            try:
                db.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL")
