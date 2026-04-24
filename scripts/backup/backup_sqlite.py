import os
import pickle
import gzip

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# Possible DB locations
CANDIDATE_PATHS = [
    os.path.join(PROJECT_ROOT, "data", "tracker.db"),
    os.path.join(PROJECT_ROOT, "demo", "backend", "data", "tracker.db"),
]

BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def find_sqlite_path():
    for path in CANDIDATE_PATHS:
        if os.path.exists(path):
            return path
    return None


def backup_sqlite():
    sqlite_path = find_sqlite_path()

    if not sqlite_path:
        print(f"[backup_sqlite] SQLite DB not found. Checked paths:")
        for p in CANDIDATE_PATHS:
            print(f" - {p}")
        print("[backup_sqlite] Skipping SQLite backup.")
        return None

    print(f"[backup_sqlite] Using DB at: {sqlite_path}")

    backup_file = os.path.join(BACKUP_DIR, "sqlite_latest.pkl.gz")

    try:
        with open(sqlite_path, "rb") as f:
            db_bytes = f.read()

        with gzip.open(backup_file, "wb") as f:
            pickle.dump(db_bytes, f)

        print(f"[backup_sqlite] Backup successful → {backup_file}")
        return backup_file

    except Exception as e:
        print(f"[backup_sqlite] Backup failed: {str(e)}")
        return None


if __name__ == "__main__":
    backup_sqlite()
