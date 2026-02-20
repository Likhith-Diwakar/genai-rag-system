from src.storage.tracker_db import TrackerDB

t = TrackerDB()
ids = t.get_all_file_ids()

print("\nTracked file IDs:")
for i in ids:
    print(i)