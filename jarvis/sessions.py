"""Persistent conversation history using SQLite."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .llm.base import Message

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "history.db"


def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_session ON messages(session)
    """)
    conn.commit()
    return conn


def save_message(session: str, msg: Message) -> None:
    """Save a single message to the session history."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO messages (session, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session, msg.role, msg.content, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def load_history(session: str, limit: int = 50) -> list[Message]:
    """Load the most recent messages from a session."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session = ? ORDER BY id DESC LIMIT ?",
            (session, limit),
        ).fetchall()
        # Reverse to get chronological order
        return [Message(role=r[0], content=r[1]) for r in reversed(rows)]
    finally:
        conn.close()


def list_sessions() -> list[dict]:
    """List all sessions with their message counts."""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT session, COUNT(*) as count, MAX(timestamp) as last_active
            FROM messages GROUP BY session ORDER BY last_active DESC
        """).fetchall()
        return [
            {"session": r[0], "count": r[1], "last_active": r[2]}
            for r in rows
        ]
    finally:
        conn.close()


def clear_session(session: str) -> int:
    """Delete all messages in a session. Returns count deleted."""
    conn = _get_conn()
    try:
        cursor = conn.execute("DELETE FROM messages WHERE session = ?", (session,))
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
