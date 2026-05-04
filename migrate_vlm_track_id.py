"""
migrate_vlm_track_id.py — Add track_id column to vlm_detections and vlm_no_results tables.
"""
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "detections.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for table in ["vlm_detections", "vlm_no_results"]:
        # Check if track_id column already exists
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if "track_id" not in columns:
            print(f"Adding track_id column to {table}...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN track_id INTEGER")
            print(f"  Done.")
        else:
            print(f"  {table} already has track_id column.")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
