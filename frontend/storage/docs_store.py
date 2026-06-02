import sqlite3
import os
from typing import List, Dict, Any
from datetime import datetime, timezone

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]  # documind-ai/
DB_PATH = str((ROOT_DIR / ".local" / "chats.db").resolve())


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_docs_table():
    with _conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS session_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            doc_id TEXT,
            doc_name TEXT,
            added_at TEXT
        )
        """)


def add_docs(session_id: str, docs: List[Dict[str, Any]]) -> None:
    with _conn() as c:
        for d in docs:
            c.execute(
                "INSERT INTO session_docs (session_id, doc_id, doc_name, added_at) VALUES (?, ?, ?, ?)",
                (
                    session_id,
                    d.get("doc_id"),
                    d.get("filename") or d.get("doc_name"),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )


def list_docs(session_id: str) -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT doc_id, doc_name FROM session_docs WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()

        return [{"doc_id": r[0], "doc_name": r[1]} for r in rows]


def get_first_doc_name(session_id: str) -> str:
    if not session_id:
        return ""
    with _conn() as c:
        row = c.execute(
            "SELECT doc_name FROM session_docs WHERE session_id = ? ORDER BY id ASC LIMIT 1",
            (session_id,),
        ).fetchone()
        return row[0] if row else ""