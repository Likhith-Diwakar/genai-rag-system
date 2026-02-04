import sqlite3
from pathlib import Path


DB_PATH = Path("data/tracker.db")


class TrackerDB:
    def __init__(self):
        DB_PATH.parent.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                file_id TEXT PRIMARY KEY,
                file_name TEXT
            )
            """
        )
        self.conn.commit()

    def is_ingested(self, file_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM files WHERE file_id = ?",
            (file_id,),
        )
        return cursor.fetchone() is not None

    def mark_ingested(self, file_id: str, file_name: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO files (file_id, file_name) VALUES (?, ?)",
            (file_id, file_name),
        )
        self.conn.commit()

    def remove(self, file_id: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM files WHERE file_id = ?",
            (file_id,),
        )
        self.conn.commit()

    def get_all_file_ids(self) -> set[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT file_id FROM files")
        rows = cursor.fetchall()
        return {row[0] for row in rows}


if __name__ == "__main__":
    tracker = TrackerDB()

    tracker.mark_ingested("file_1", "Test File")
    print(tracker.is_ingested("file_1"))   # True
    print(tracker.get_all_file_ids())

    tracker.remove("file_1")
    print(tracker.is_ingested("file_1"))   # False