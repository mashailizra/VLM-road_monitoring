import sqlite3
import os
import shutil

DB_PATH = "detections.db"
STATIC_DIR = "static"

def rectify():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Reorganize Filesystem
    moves = [
        # Source (relative to static), Destination (relative to static)
        ("live_history/VLM-YES", "live_history/vlm_detect/vlm_yes"),
        ("live_history/VLM-NO", "live_history/vlm_detect/vlm_no"),
        ("images/yolo", "live_history/yolo_detect/accepted"),
        ("yolo_detect/accepted", "live_history/yolo_detect/accepted"),
        ("vlm_detect/accepted", "live_history/vlm_detect/vlm_yes"),
        ("vlm_detect/rejected", "live_history/vlm_detect/vlm_no"),
    ]

    for src_rel, dst_rel in moves:
        src = os.path.join(STATIC_DIR, src_rel.replace("/", os.sep))
        dst = os.path.join(STATIC_DIR, dst_rel.replace("/", os.sep))
        
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            print(f"Moving {src} to {dst}...")
            # If destination exists and is a directory, move contents. Otherwise move directory.
            if os.path.exists(dst):
                for item in os.listdir(src):
                    s = os.path.join(src, item)
                    d = os.path.join(dst, item)
                    if not os.path.exists(d):
                        shutil.move(s, d)
                os.rmdir(src)
            else:
                shutil.move(src, dst)
        else:
            print(f"Source {src} not found, skipping move.")

    # 2. Update Database Paths
    # We need to update:
    # vlm_detections: image column
    # vlm_no_results: image column
    # detections: image column

    updates = [
        # Table, Column, Old prefix, New prefix
        ("vlm_detections", "image", "vlm_detect/accepted/", "live_history/vlm_detect/vlm_yes/"),
        ("vlm_detections", "image", "live_history/VLM-YES/", "live_history/vlm_detect/vlm_yes/"),
        
        ("vlm_no_results", "image", "vlm_detect/rejected/", "live_history/vlm_detect/vlm_no/"),
        ("vlm_no_results", "image", "live_history/VLM-NO/", "live_history/vlm_detect/vlm_no/"),
        
        ("detections", "image", "yolo_detect/accepted/", "live_history/yolo_detect/accepted/"),
        ("detections", "image", "yolo_detect/rejected/", "live_history/yolo_detect/rejected/"),
        ("detections", "image", "images/yolo/", "live_history/yolo_detect/accepted/"),
        ("detections", "image", "yolo/", "live_history/yolo_detect/accepted/"),
    ]

    for table, col, old_pre, new_pre in updates:
        print(f"Updating {table}.{col}: '{old_pre}' -> '{new_pre}'")
        # Use simple string replacement for sqlite3
        cur.execute(f"""
            UPDATE {table} 
            SET {col} = REPLACE({col}, ?, ?)
            WHERE {col} LIKE ?
        """, (old_pre, new_pre, old_pre + '%'))
    
    conn.commit()
    print("Database paths rectified.")
    conn.close()

if __name__ == "__main__":
    rectify()
