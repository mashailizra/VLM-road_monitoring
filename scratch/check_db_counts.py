import sqlite3
import os

DB_PATH = "detections.db"

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    tables = ["detections", "vlm_detections", "vlm_no_results", "live_feed_history"]
    for table in tables:
        try:
            cur.execute(f"SELECT count(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"{table}: {count} rows")
        except sqlite3.OperationalError as e:
            print(f"Error querying {table}: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_db()
