import sqlite3
import os
import json

DB_PATH = "detections.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("Fetching history...")
    cur.execute("SELECT * FROM live_feed_history")
    rows = cur.fetchall()
    print(f"Found {len(rows)} rows to migrate.")

    for r in rows:
        route = r['route'] or "UNKNOWN"
        label = r['label'] or "unknown"
        confidence = r['confidence'] or 0.0
        image_path = r['image']
        track_id = r['track_id']
        reasoning = r['reasoning']
        timestamp = r['timestamp']
        
        # Try to extract model_name from meta_json if possible
        model_name = "legacy-migrated"
        if r['meta_json']:
            try:
                meta = json.loads(r['meta_json'])
                model_name = meta.get("model_name") or meta.get("model") or model_name
            except:
                pass

        # 1. Insert into detections
        det_status = 'accepted'
        if "REJECT" in route or "NO" in route:
            det_status = 'rejected'
        
        cur.execute(
            """INSERT INTO detections (defect_type, confidence, model_name, image, track_id, status, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (label, confidence, model_name, image_path, track_id, det_status, timestamp)
        )

        # 2. VLM specific tables
        if route == "VLM-YES":
            cur.execute(
                """INSERT INTO vlm_detections (defect_type, image, model, reasoning, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (label, image_path, model_name, reasoning, timestamp)
            )
        elif route == "VLM-NO":
            cur.execute(
                """INSERT INTO vlm_no_results (defect_type, image, model, reasoning, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (label, image_path, model_name, reasoning, timestamp)
            )

    conn.commit()
    print("Migration complete!")
    conn.close()

if __name__ == "__main__":
    migrate()
