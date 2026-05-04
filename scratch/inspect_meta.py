import sqlite3
import json

DB_PATH = "detections.db"

def inspect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT meta_json FROM live_feed_history LIMIT 5")
    rows = cur.fetchall()
    
    for i, r in enumerate(rows):
        print(f"Row {i} meta_json:")
        try:
            meta = json.loads(r['meta_json'])
            print(json.dumps(meta, indent=2))
        except:
            print(r['meta_json'])
        print("-" * 20)
    
    conn.close()

if __name__ == "__main__":
    inspect()
