import sqlite3
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "chats.db"))


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id TEXT PRIMARY KEY,
            title TEXT,
            session_id TEXT,
            created_at TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
        """)


def create_chat(chat_id: str, title: str, session_id: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO chats (chat_id, title, session_id, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, title, session_id, datetime.now(timezone.utc).isoformat())
        )


def list_chats() -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT chat_id, title, session_id, created_at FROM chats ORDER BY created_at DESC"
        ).fetchall()

        return [
            {
                "chat_id": r[0],
                "title": r[1],
                "session_id": r[2],
                "created_at": r[3]
            }
            for r in rows
        ]


def delete_chat(chat_id: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        c.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))


def add_message(chat_id: str, role: str, content: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO messages (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, datetime.now(timezone.utc).isoformat())
        )


def update_chat_session_id(chat_id: str, session_id: str) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE chats SET session_id = ? WHERE chat_id = ?",
            (session_id, chat_id)
        )


def get_messages(chat_id: str) -> List[Dict[str, str]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id ASC",
            (chat_id,)
        ).fetchall()

        return [{"role": r[0], "content": r[1]} for r in rows]