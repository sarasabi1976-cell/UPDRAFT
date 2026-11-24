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
        """)
