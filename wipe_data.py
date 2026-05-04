import sqlite3
import os
import shutil

DB_PATH = "detections.db"
STATIC_DIR = "static"

def wipe():
    # 1. Clear Database
    if os.path.exists(DB_PATH):
        print("Clearing database tables...")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        tables = ["detections", "vlm_detections", "vlm_no_results", "live_feed_history"]
        for table in tables:
            try:
                cur.execute(f"DELETE FROM {table}")
                print(f"  Cleared {table}")
            except Exception as e:
                print(f"  Could not clear {table}: {e}")
        
        # Reset auto-increment counters
        try:
            cur.execute("DELETE FROM sqlite_sequence")
        except:
            pass
            
        conn.commit()
        conn.close()
        print("Database cleared.")
    else:
        print("Database not found.")

    # 2. Clear Images
    image_dirs = [
        "live_history/vlm_detect/vlm_yes",
        "live_history/vlm_detect/vlm_no",
        "live_history/yolo_detect/accepted",
        "live_history/yolo_detect/rejected",
        "live_history/VLM-YES",
        "live_history/VLM-NO",
        "images/yolo",
        "yolo_detect/accepted"
    ]
    
    print("Clearing image directories...")
    for d_rel in image_dirs:
        d_path = os.path.join(STATIC_DIR, d_rel.replace("/", os.sep))
        if os.path.exists(d_path):
            print(f"  Emptying {d_path}")
            for item in os.listdir(d_path):
                i_path = os.path.join(d_path, item)
                try:
                    if os.path.isfile(i_path):
                        os.unlink(i_path)
                    elif os.path.is_dir(i_path):
                        shutil.rmtree(i_path)
                except Exception as e:
                    print(f"    Failed to delete {item}: {e}")
        else:
            print(f"  Directory {d_path} not found.")
            
    print("Cleanup complete.")

if __name__ == "__main__":
    wipe()
