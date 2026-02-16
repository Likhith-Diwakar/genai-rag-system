import os
import sqlite3
import pandas as pd
from src.logger import logger

DB_PATH = "data/csv_store.db"


class SQLiteStore:

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)

    # -------------------------------------------------
    # Safe table name formatting
    # -------------------------------------------------
    def _safe_table_name(self, file_name: str):
        return file_name.replace(".", "_").replace(" ", "_")

    # -------------------------------------------------
    # Store dataframe into SQLite
    # -------------------------------------------------
    def store_dataframe(self, file_name: str, df: pd.DataFrame):
        table_name = self._safe_table_name(file_name)
        logger.info(f"Storing CSV in SQLite table: {table_name}")
        df.to_sql(table_name, self.conn, if_exists="replace", index=False)

    # -------------------------------------------------
    # Load dataframe from SQLite
    # -------------------------------------------------
    def load_dataframe(self, file_name: str):
        table_name = self._safe_table_name(file_name)
        try:
            return pd.read_sql_query(
                f"SELECT * FROM '{table_name}'",
                self.conn
            )
        except Exception:
            logger.warning(f"SQLite table not found: {table_name}")
            return None

    # -------------------------------------------------
    # Check if table exists
    # -------------------------------------------------
    def table_exists(self, file_name: str):
        table_name = self._safe_table_name(file_name)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return cursor.fetchone() is not None

    # -------------------------------------------------
    # 🔥 Required for RAG: List all tables
    # -------------------------------------------------
    def list_tables(self):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        )
        return [row[0] for row in cursor.fetchall()]
