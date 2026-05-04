import sqlite3
import os

DB_PATH = "detections.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found. Nothing to migrate.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if 'status' column already exists
    cur.execute("PRAGMA table_info(detections)")
    columns = [row[1] for row in cur.fetchall()]
    
    if "status" not in columns:
        print("Adding 'status' column to 'detections' table...")
        try:
            cur.execute("ALTER TABLE detections ADD COLUMN status TEXT DEFAULT 'accepted'")
            conn.commit()
            print("Migration successful: added 'status' column.")
        except Exception as e:
            print(f"Migration failed: {e}")
    else:
        print("'status' column already exists in 'detections' table.")
    
    conn.close()

if __name__ == "__main__":
    migrate()
