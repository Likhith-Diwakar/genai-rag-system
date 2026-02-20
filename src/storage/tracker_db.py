import sqlite3
from pathlib import Path
from threading import Lock

DB_PATH = Path("data/tracker.db")


class TrackerDB:
    _lock = Lock()  # Ensures safe writes across background threads

    def __init__(self):
        DB_PATH.parent.mkdir(exist_ok=True)

        # Thread-safe connection
        self.conn = sqlite3.connect(
            DB_PATH,
            check_same_thread=False
        )

        #  Enable WAL mode for better concurrency
        self.conn.execute("PRAGMA journal_mode=WAL;")

        self._create_table()

    def _create_table(self):
        with self._lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    file_id TEXT PRIMARY KEY,
                    file_name TEXT
                )
            """)
            self.conn.commit()

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

    def get_all_file_ids(self) -> set[str]:
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
