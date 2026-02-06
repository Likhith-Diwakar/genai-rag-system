import sqlite3
from pathlib import Path
from src.logger import logger

DB_PATH = Path("data/tracker.db")


class TrackerDB:
    def __init__(self):
        DB_PATH.parent.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self._create_table()

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                file_id TEXT PRIMARY KEY,
                file_name TEXT
            )
        """)
        self.conn.commit()

    def is_ingested(self, file_id: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM files WHERE file_id=?", (file_id,))
        exists = cur.fetchone() is not None
        logger.debug(f"Tracker check | {file_id} ingested={exists}")
        return exists

    def mark_ingested(self, file_id: str, file_name: str):
        logger.info(f"Marking ingested: {file_name}")
        self.conn.execute(
            "INSERT OR IGNORE INTO files VALUES (?, ?)",
            (file_id, file_name)
        )
        self.conn.commit()

    def remove(self, file_id: str):
        logger.warning(f"Removing tracker entry: {file_id}")
        self.conn.execute("DELETE FROM files WHERE file_id=?", (file_id,))
        self.conn.commit()

    def get_all_file_ids(self) -> set[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT file_id FROM files")
        return {r[0] for r in cur.fetchall()}
