"""SQLite — yuk sessiyalari va qatnashuvchilar."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any

from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS load_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'draft',
    masul_id INTEGER NOT NULL,
    masul_name TEXT NOT NULL,
    car_photo_start TEXT,
    unload_photo_start TEXT,
    car_photo_end TEXT,
    unload_photo_end TEXT,
    group_chat_id INTEGER,
    group_album_msg_id INTEGER,
    group_status_msg_id INTEGER,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    user_name TEXT NOT NULL,
    username TEXT,
    joined_at TEXT NOT NULL,
    personal_msg_id INTEGER,
    pause_total_sec INTEGER NOT NULL DEFAULT 0,
    paused_at TEXT,
    UNIQUE(session_id, user_id),
    FOREIGN KEY (session_id) REFERENCES load_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON load_sessions(status);
CREATE INDEX IF NOT EXISTS idx_participants_session ON participants(session_id);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings()["db_path"], check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate_participants(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(participants)")}
    if "pause_total_sec" not in cols:
        conn.execute(
            "ALTER TABLE participants ADD COLUMN pause_total_sec INTEGER NOT NULL DEFAULT 0"
        )
    if "paused_at" not in cols:
        conn.execute("ALTER TABLE participants ADD COLUMN paused_at TEXT")


def init_db() -> None:
    with db() as conn:
        conn.executescript(SCHEMA)
        _migrate_participants(conn)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def get_active_session() -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(
            """
            SELECT * FROM load_sessions
            WHERE status IN ('active', 'finishing')
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        return row_to_dict(row)


def create_session(*, masul_id: int, masul_name: str) -> int:
    from time_util import now_iso

    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO load_sessions (status, masul_id, masul_name, created_at)
            VALUES ('draft', ?, ?, ?)
            """,
            (masul_id, masul_name, now_iso()),
        )
        return int(cur.lastrowid)


def update_session(session_id: int, **fields: Any) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [session_id]
    with db() as conn:
        conn.execute(f"UPDATE load_sessions SET {cols} WHERE id=?", vals)


def get_session(session_id: int) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM load_sessions WHERE id=?", (session_id,)
        ).fetchone()
        return row_to_dict(row)


def list_participants(session_id: int) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM participants
            WHERE session_id=?
            ORDER BY joined_at ASC, id ASC
            """,
            (session_id,),
        ).fetchall()
        return [row_to_dict(r) for r in rows]


def add_participant(
    *,
    session_id: int,
    user_id: int,
    user_name: str,
    username: str | None,
    personal_msg_id: int | None = None,
) -> bool:
    from time_util import now_iso

    with db() as conn:
        try:
            conn.execute(
                """
                INSERT INTO participants
                (session_id, user_id, user_name, username, joined_at, personal_msg_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    user_id,
                    user_name,
                    username or "",
                    now_iso(),
                    personal_msg_id,
                ),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def update_participant_personal_msg(
    session_id: int, user_id: int, personal_msg_id: int
) -> None:
    with db() as conn:
        conn.execute(
            """
            UPDATE participants SET personal_msg_id=?
            WHERE session_id=? AND user_id=?
            """,
            (personal_msg_id, session_id, user_id),
        )


def get_participant(session_id: int, user_id: int) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM participants WHERE session_id=? AND user_id=?",
            (session_id, user_id),
        ).fetchone()
        return row_to_dict(row)


def pause_participant(session_id: int, user_id: int) -> bool:
    from time_util import now_iso

    with db() as conn:
        row = conn.execute(
            "SELECT paused_at FROM participants WHERE session_id=? AND user_id=?",
            (session_id, user_id),
        ).fetchone()
        if not row or row["paused_at"]:
            return False
        conn.execute(
            "UPDATE participants SET paused_at=? WHERE session_id=? AND user_id=?",
            (now_iso(), session_id, user_id),
        )
        return True


def resume_participant(session_id: int, user_id: int) -> bool:
    from time_util import now_iso

    with db() as conn:
        row = conn.execute(
            """
            SELECT paused_at, pause_total_sec FROM participants
            WHERE session_id=? AND user_id=?
            """,
            (session_id, user_id),
        ).fetchone()
        if not row or not row["paused_at"]:
            return False
        from time_util import parse_iso

        start = parse_iso(row["paused_at"])
        end = parse_iso(now_iso())
        extra = max(0, int((end - start).total_seconds())) if start and end else 0
        conn.execute(
            """
            UPDATE participants
            SET paused_at=NULL, pause_total_sec=pause_total_sec+?
            WHERE session_id=? AND user_id=?
            """,
            (extra, session_id, user_id),
        )
        return True


def participant_exists(session_id: int, user_id: int) -> bool:
    with db() as conn:
        row = conn.execute(
            "SELECT 1 FROM participants WHERE session_id=? AND user_id=?",
            (session_id, user_id),
        ).fetchone()
        return row is not None


def cancel_draft_session(session_id: int) -> None:
    with db() as conn:
        conn.execute(
            "DELETE FROM load_sessions WHERE id=? AND status='draft'",
            (session_id,),
        )


def abandon_session(session_id: int) -> None:
    with db() as conn:
        conn.execute("DELETE FROM participants WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM load_sessions WHERE id=?", (session_id,))
