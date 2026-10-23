import os
import secrets
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "focusflow.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            tag TEXT DEFAULT 'Study',
            duration_minutes INTEGER DEFAULT 85,
            completed BOOLEAN DEFAULT 0,
            completed_time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_list_id TEXT,
            title TEXT NOT NULL,
            tag TEXT DEFAULT 'Study',
            duration_minutes INTEGER DEFAULT 45,
            priority TEXT DEFAULT 'medium',
            notes TEXT DEFAULT '',
            recurrence_rule TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            occurrence_limit INTEGER,
            due_offset_days INTEGER,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_tokens (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            revoked INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS focus_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            client_session_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT NOT NULL,
            study_date TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL CHECK (duration_seconds >= 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
        )
    """)
    cursor.execute("PRAGMA table_info(focus_sessions)")
    session_columns = {row["name"] for row in cursor.fetchall()}
    if "study_date" not in session_columns:
        cursor.execute("ALTER TABLE focus_sessions ADD COLUMN study_date TEXT")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_focus_sessions_task "
        "ON focus_sessions(user_id, task_id, started_at)"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_focus_sessions_idempotency "
        "ON focus_sessions(user_id, client_session_id)"
    )

    cursor.execute("PRAGMA table_info(tasks)")
    task_columns = {row["name"] for row in cursor.fetchall()}
    task_migrations = {
        "task_list_id": "TEXT",
        "scheduled_date": "TEXT",
        "occurrence_date": "TEXT",
        "due_date": "TEXT",
        "series_id": "INTEGER",
        "priority": "TEXT NOT NULL DEFAULT 'medium'",
        "notes": "TEXT NOT NULL DEFAULT ''",
        "skipped": "INTEGER NOT NULL DEFAULT 0",
        "actual_duration_seconds": "INTEGER NOT NULL DEFAULT 0",
        "completed_at": "TEXT",
    }
    for column, definition in task_migrations.items():
        if column not in task_columns:
            cursor.execute(f"ALTER TABLE tasks ADD COLUMN {column} {definition}")

    cursor.execute(
        "UPDATE tasks SET occurrence_date = scheduled_date "
        "WHERE series_id IS NOT NULL AND occurrence_date IS NULL"
    )

    cursor.execute("PRAGMA table_info(task_series)")
    series_columns = {row["name"] for row in cursor.fetchall()}
    if "due_offset_days" not in series_columns:
        cursor.execute("ALTER TABLE task_series ADD COLUMN due_offset_days INTEGER")

    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_task_occurrence_series_date "
        "ON tasks(series_id, scheduled_date) "
        "WHERE series_id IS NOT NULL AND scheduled_date IS NOT NULL"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_task_occurrence_identity "
        "ON tasks(series_id, occurrence_date) "
        "WHERE series_id IS NOT NULL AND occurrence_date IS NOT NULL"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_user_scheduled "
        "ON tasks(user_id, scheduled_date)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_user_due ON tasks(user_id, due_date)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_task_series_user_active "
        "ON task_series(user_id, active)"
    )

    # Stats / streak table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY,
            streak_days INTEGER DEFAULT 3,
            focus_minutes_today INTEGER DEFAULT 0,
            focus_minutes_week INTEGER DEFAULT 1455,
            focus_seconds_today INTEGER DEFAULT 0,
            stats_date TEXT,
            focus_seconds_week INTEGER DEFAULT 0,
            stats_week_start TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("PRAGMA table_info(user_stats)")
    stats_columns = {row["name"] for row in cursor.fetchall()}
    if "focus_seconds_today" not in stats_columns:
        cursor.execute(
            "ALTER TABLE user_stats ADD COLUMN focus_seconds_today INTEGER DEFAULT 0"
        )
    if "stats_date" not in stats_columns:
        cursor.execute("ALTER TABLE user_stats ADD COLUMN stats_date TEXT")
    if "focus_seconds_week" not in stats_columns:
        cursor.execute(
            "ALTER TABLE user_stats ADD COLUMN focus_seconds_week INTEGER DEFAULT 0"
        )
    if "stats_week_start" not in stats_columns:
        cursor.execute("ALTER TABLE user_stats ADD COLUMN stats_week_start TEXT")

    # Older installs may already have the publicly documented demo account.
    # Preserve its task history, but invalidate the shared password and tokens.
    cursor.execute(
        "SELECT id, password_hash FROM users "
        "WHERE username = ? AND email = ?",
        ("Alex", "alex@focusflow.app"),
    )
    demo_user = cursor.fetchone()
    if demo_user and check_password_hash(demo_user["password_hash"], "password123"):
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(secrets.token_urlsafe(48)), demo_user["id"]),
        )
        cursor.execute(
            "UPDATE api_tokens SET revoked = 1 WHERE user_id = ?",
            (demo_user["id"],),
        )

    conn.commit()
    conn.close()
