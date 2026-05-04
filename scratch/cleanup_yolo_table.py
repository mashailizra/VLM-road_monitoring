import sqlite3
import os

DB_PATH = "detections.db"

def cleanup():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("Aligning detections table with new rules (only > 0.80)...")
    
    # Remove anything that is not high-confidence from the main detections table.
    # Note: Confirmed VLM detections (0.3 - 0.8) should stay in vlm_detections table, 
    # and they were previously being duplicated in the detections table.
    cur.execute("DELETE FROM detections WHERE confidence < 0.80")
    print(f"Deleted {cur.rowcount} rows from detections table.")

    conn.commit()
    print("Database cleanup complete!")
    conn.close()

if __name__ == "__main__":
    cleanup()
