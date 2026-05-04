import sqlite3
import os

DB_PATH = "detections.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found. Nothing to migrate.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if columns exist
    cur.execute("PRAGMA table_info(detections)")
    columns = [row[1] for row in cur.fetchall()]
    
    # Migrate 'status' if missing
    if "status" not in columns:
        print("Adding 'status' column to 'detections' table...")
        try:
            cur.execute("ALTER TABLE detections ADD COLUMN status TEXT DEFAULT 'accepted'")
            conn.commit()
            print("Migration successful: added 'status' column.")
        except Exception as e:
            print(f"Migration failed (status): {e}")
    else:
        print("'status' column already exists.")

    # Migrate 'reasoning' if missing
    if "reasoning" not in columns:
        print("Adding 'reasoning' column to 'detections' table...")
        try:
            cur.execute("ALTER TABLE detections ADD COLUMN reasoning TEXT")
            conn.commit()
            print("Migration successful: added 'reasoning' column.")
        except Exception as e:
            print(f"Migration failed (reasoning): {e}")
    else:
        print("'reasoning' column already exists.")
    
    conn.close()

if __name__ == "__main__":
    migrate()
