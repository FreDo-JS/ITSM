# ai-generated: 100% - Claude Code wrote the SQLite store from API.md section 10
"""Ticket persistence: one SQLite file (R-23), tickets stored as JSON documents."""

import json
import os
import sqlite3
import threading
from pathlib import Path


class TicketStore:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS tickets (id TEXT PRIMARY KEY, doc TEXT NOT NULL)")
        self._db.commit()

    def put(self, ticket: dict) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO tickets (id, doc) VALUES (?, ?)",
                (ticket["id"], json.dumps(ticket)),
            )
            self._db.commit()

    def get(self, ticket_id: str) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT doc FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT doc FROM tickets").fetchall()
        return [json.loads(r[0]) for r in rows]


def open_store() -> TicketStore:
    return TicketStore(os.environ.get("SVCDESK_DB", "svcdesk.db"))
