"""SQLite storage layer.

Everything the bot remembers lives in one file: studybot.sqlite3
Inside that file there are 5 tables:
  users      - settings (timezone, daily reminder)
  tasks      - your study tasks / homework
  flashcards - question + answer pairs you add yourself
  study_log  - minutes studied per day (powers the stats)
  quiz_log   - your quiz scores
"""
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

from config import DB_PATH

_lock = threading.Lock()
_conn = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    """Open (once) and return the shared database connection."""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        init_db(_conn)
    return _conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    """Create the tables if they are not there yet."""
    conn = conn or connect()
    with _lock:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY,
                username      TEXT,
                timezone      TEXT DEFAULT 'UTC',
                reminder_time TEXT,
                created_at    TEXT
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                title        TEXT NOT NULL,
                subject      TEXT DEFAULT 'General',
                priority     TEXT DEFAULT 'Medium',
                status       TEXT DEFAULT 'pending',
                due_date     TEXT,
                created_at   TEXT,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS flashcards (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                question   TEXT NOT NULL,
                answer     TEXT NOT NULL,
                subject    TEXT DEFAULT 'General',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS study_log (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                day     TEXT NOT NULL,
                minutes INTEGER NOT NULL DEFAULT 0,
                subject TEXT DEFAULT 'General'
            );

            CREATE TABLE IF NOT EXISTS quiz_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                correct    INTEGER NOT NULL DEFAULT 0,
                total      INTEGER NOT NULL DEFAULT 0,
                created_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
            CREATE INDEX IF NOT EXISTS idx_cards_user ON flashcards(user_id);
            CREATE INDEX IF NOT EXISTS idx_log_user_day ON study_log(user_id, day);
            """
        )
        conn.commit()


# --------------------------------------------------------------------------
# users
# --------------------------------------------------------------------------
def ensure_user(user_id: int, username: str | None = None) -> None:
    """Create the user row the first time we see them."""
    conn = connect()
    with _lock:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, timezone, created_at) VALUES (?,?,?,?)",
            (user_id, username, "UTC", _now()),
        )
        conn.commit()


def get_user(user_id: int) -> dict:
    conn = connect()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    return dict(row) if row else {}


def set_timezone(user_id: int, tz: str) -> None:
    conn = connect()
    with _lock:
        conn.execute("UPDATE users SET timezone=? WHERE user_id=?", (tz, user_id))
        conn.commit()


def set_reminder(user_id: int, hhmm: str) -> None:
    conn = connect()
    with _lock:
        conn.execute("UPDATE users SET reminder_time=? WHERE user_id=?", (hhmm, user_id))
        conn.commit()


def clear_reminder(user_id: int) -> None:
    conn = connect()
    with _lock:
        conn.execute("UPDATE users SET reminder_time=NULL WHERE user_id=?", (user_id,))
        conn.commit()


# --------------------------------------------------------------------------
# tasks
# --------------------------------------------------------------------------
def add_task(user_id, title, subject="General", priority="Medium", due_date=None) -> int:
    conn = connect()
    with _lock:
        cur = conn.execute(
            """INSERT INTO tasks (user_id, title, subject, priority, status, due_date, created_at)
               VALUES (?,?,?,?,'pending',?,?)""",
            (user_id, title, subject, priority, due_date, _now()),
        )
        conn.commit()
        return cur.lastrowid


def list_tasks(user_id: int, status: str | None = None) -> list[dict]:
    conn = connect()
    if status:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? AND status=? ORDER BY id DESC", (user_id, status)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_task(user_id: int, task_id: int) -> dict | None:
    conn = connect()
    row = conn.execute(
        "SELECT * FROM tasks WHERE user_id=? AND id=?", (user_id, task_id)
    ).fetchone()
    return dict(row) if row else None


def set_task_status(user_id: int, task_id: int, status: str) -> bool:
    conn = connect()
    with _lock:
        completed = _now() if status == "done" else None
        cur = conn.execute(
            "UPDATE tasks SET status=?, completed_at=? WHERE user_id=? AND id=?",
            (status, completed, user_id, task_id),
        )
        conn.commit()
        return cur.rowcount > 0


def delete_task(user_id: int, task_id: int) -> bool:
    conn = connect()
    with _lock:
        cur = conn.execute("DELETE FROM tasks WHERE user_id=? AND id=?", (user_id, task_id))
        conn.commit()
        return cur.rowcount > 0


def task_counts(user_id: int) -> dict:
    conn = connect()
    row = conn.execute(
        """SELECT
             COUNT(*) AS total,
             SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
             SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done
           FROM tasks WHERE user_id=?""",
        (user_id,),
    ).fetchone()
    return {
        "total": row["total"] or 0,
        "pending": row["pending"] or 0,
        "done": row["done"] or 0,
    }


def tasks_due(user_id: int, day: str) -> list[dict]:
    """Tasks whose due_date is today or already overdue."""
    conn = connect()
    rows = conn.execute(
        """SELECT * FROM tasks
           WHERE user_id=? AND status='pending'
             AND due_date IS NOT NULL AND due_date <= ?
           ORDER BY due_date ASC""",
        (user_id, day),
    ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# flashcards
# --------------------------------------------------------------------------
def add_flashcard(user_id, question, answer, subject="General") -> int:
    conn = connect()
    with _lock:
        cur = conn.execute(
            "INSERT INTO flashcards (user_id, question, answer, subject, created_at) VALUES (?,?,?,?,?)",
            (user_id, question, answer, subject, _now()),
        )
        conn.commit()
        return cur.lastrowid


def list_flashcards(user_id: int, subject: str | None = None, limit: int = 100) -> list[dict]:
    conn = connect()
    if subject:
        rows = conn.execute(
            "SELECT * FROM flashcards WHERE user_id=? AND lower(subject)=lower(?) ORDER BY RANDOM() LIMIT ?",
            (user_id, subject, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM flashcards WHERE user_id=? ORDER BY RANDOM() LIMIT ?", (user_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def flashcard_count(user_id: int) -> int:
    conn = connect()
    row = conn.execute("SELECT COUNT(*) AS c FROM flashcards WHERE user_id=?", (user_id,)).fetchone()
    return row["c"] or 0


def delete_flashcard(user_id: int, card_id: int) -> bool:
    conn = connect()
    with _lock:
        cur = conn.execute("DELETE FROM flashcards WHERE user_id=? AND id=?", (user_id, card_id))
        conn.commit()
        return cur.rowcount > 0


# --------------------------------------------------------------------------
# study log + stats
# --------------------------------------------------------------------------
def log_study(user_id: int, minutes: int, subject: str = "General") -> None:
    conn = connect()
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _lock:
        conn.execute(
            "INSERT INTO study_log (user_id, day, minutes, subject) VALUES (?,?,?,?)",
            (user_id, day, minutes, subject),
        )
        conn.commit()


def last_days(user_id: int, days: int = 7) -> list[tuple[str, int]]:
    """Return [(day_string, minutes), ...] oldest first."""
    conn = connect()
    since = (datetime.now(timezone.utc) - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    rows = conn.execute(
        """SELECT day, SUM(minutes) AS m FROM study_log
           WHERE user_id=? AND day >= ? GROUP BY day""",
        (user_id, since),
    ).fetchall()
    lookup = {r["day"]: r["m"] for r in rows}
    out = []
    for i in range(days - 1, -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        out.append((d, lookup.get(d, 0)))
    return out


def total_minutes(user_id: int) -> int:
    conn = connect()
    row = conn.execute(
        "SELECT COALESCE(SUM(minutes),0) AS m FROM study_log WHERE user_id=?", (user_id,)
    ).fetchone()
    return row["m"] or 0


def streak(user_id: int) -> int:
    """Consecutive days (ending today or yesterday) with at least 1 minute studied."""
    conn = connect()
    rows = conn.execute(
        "SELECT DISTINCT day FROM study_log WHERE user_id=? AND minutes > 0", (user_id,)
    ).fetchall()
    days = {r["day"] for r in rows}
    today = datetime.now(timezone.utc).date()
    count = 0
    cursor = today
    # allow the streak to still be alive if today has no session yet
    if cursor.isoformat() not in days:
        cursor = today - timedelta(days=1)
    while cursor.isoformat() in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def log_quiz(user_id: int, correct: int, total: int) -> None:
    conn = connect()
    with _lock:
        conn.execute(
            "INSERT INTO quiz_log (user_id, correct, total, created_at) VALUES (?,?,?,?)",
            (user_id, correct, total, _now()),
        )
        conn.commit()


def quiz_totals(user_id: int) -> dict:
    conn = connect()
    row = conn.execute(
        """SELECT COALESCE(SUM(correct),0) AS c, COALESCE(SUM(total),0) AS t
           FROM quiz_log WHERE user_id=?""",
        (user_id,),
    ).fetchone()
    correct, total = row["c"] or 0, row["t"] or 0
    pct = round(correct * 100 / total) if total else 0
    return {"correct": correct, "total": total, "percent": pct}
