# src/storage/tracker_db.py

import os
import sqlite3
from pathlib import Path
from threading import Lock

# ----------------------------------------------------------
# Dynamic data directory (Local + Production safe)
# ----------------------------------------------------------

BASE_DATA_DIR = os.getenv("DATA_DIR", "data")
DB_PATH = Path(BASE_DATA_DIR) / "tracker.db"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class TrackerDB:
    _lock = Lock()  # Ensures safe writes across background threads

    def __init__(self):

        # Thread-safe connection
        self.conn = sqlite3.connect(
            DB_PATH,
            check_same_thread=False
        )

        # Enable WAL mode for better concurrency
        self.conn.execute("PRAGMA journal_mode=WAL;")

        self._create_table()

    def _create_table(self):
        with self._lock:
            # Existing files tracking table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    file_id TEXT PRIMARY KEY,
                    file_name TEXT
                )
            """)

            # ── Latest Documents table ───────────────────────────────────
            # Stores the top 5 most recently ingested files globally.
            # Used by the Dashboard 'Latest Documents' card.
            # No session_id — global across all users.
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS latest_documents (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id    TEXT    UNIQUE,
                    file_name  TEXT    NOT NULL,
                    file_url   TEXT    NOT NULL,
                    ingested_at TEXT   DEFAULT (datetime('now'))
                )
            """)

            self.conn.commit()

    # ──────────────────────────────────────────────────────────────
    # files table methods
    # ──────────────────────────────────────────────────────────────

    def is_ingested(self, file_id: str) -> bool:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT 1 FROM files WHERE file_id=?",
            (file_id,)
        )
        return cur.fetchone() is not None

    def mark_ingested(self, file_id: str, file_name: str):
        with self._lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO files (file_id, file_name) VALUES (?, ?)",
                (file_id, file_name)
            )
            self.conn.commit()

    def remove(self, file_id: str):
        with self._lock:
            self.conn.execute(
                "DELETE FROM files WHERE file_id=?",
                (file_id,)
            )
            self.conn.commit()

    def get_all_file_ids(self) -> set:
        cur = self.conn.cursor()
        cur.execute("SELECT file_id FROM files")
        return {row[0] for row in cur.fetchall()}

    def get_file_name(self, file_id: str):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT file_name FROM files WHERE file_id=?",
            (file_id,)
        )
        row = cur.fetchone()
        return row[0] if row else None

    def close(self):
        self.conn.close()

    # ──────────────────────────────────────────────────────────────
    # latest_documents table methods
    # ──────────────────────────────────────────────────────────────

    def add_latest_document(self, file_id: str, file_name: str, file_url: str):
        """
        Insert a newly ingested file into latest_documents.
        - Skips if file_id already exists (no duplicates).
        - After insert, keeps only the 5 most recent rows.
        Called from ingestion pipeline (main.py) on new file detection.
        """
        with self._lock:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO latest_documents (file_id, file_name, file_url)
                VALUES (?, ?, ?)
                """,
                (file_id, file_name, file_url)
            )

            # Keep only the top 5 newest rows — prune the rest
            self.conn.execute(
                """
                DELETE FROM latest_documents
                WHERE id NOT IN (
                    SELECT id FROM latest_documents
                    ORDER BY ingested_at DESC, id DESC
                    LIMIT 5
                )
                """
            )

            self.conn.commit()

    def get_latest_documents(self, limit: int = 5) -> list:
        """
        Returns the top N most recently ingested files.
        Each item: { file_id, file_name, file_url, ingested_at }
        Used by /latest-documents API endpoint.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT file_id, file_name, file_url, ingested_at
            FROM latest_documents
            ORDER BY ingested_at DESC, id DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cur.fetchall()
        return [
            {
                "file_id":     row[0],
                "file_name":   row[1],
                "file_url":    row[2],
                "ingested_at": row[3],
            }
            for row in rows
        ]