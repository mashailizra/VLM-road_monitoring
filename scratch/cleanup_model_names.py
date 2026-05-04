import sqlite3
import os

DB_PATH = "detections.db"

def cleanup():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("Cleaning up model names...")
    
    # 1. Update detections table
    # Replace 'legacy-migrated', 'legacy-pipe', and 'best.pt' with 'yolov11n'
    cur.execute("""
        UPDATE detections 
        SET model_name = 'yolov11n' 
        WHERE model_name IN ('legacy-migrated', 'legacy-pipe', 'best.pt')
    """)
    print(f"Updated {cur.rowcount} rows in detections table.")

    # 2. Update vlm_detections table
    # Replace placeholders with the actual VLM model ID
    cur.execute("""
        UPDATE vlm_detections 
        SET model = 'Qwen/Qwen3.5-2B' 
        WHERE model IN ('legacy-migrated', 'legacy-pipe', 'best.pt')
    """)
    print(f"Updated {cur.rowcount} rows in vlm_detections table.")

    # 3. Update vlm_no_results table
    cur.execute("""
        UPDATE vlm_no_results 
        SET model = 'Qwen/Qwen3.5-2B' 
        WHERE model IN ('legacy-migrated', 'legacy-pipe', 'best.pt')
    """)
    print(f"Updated {cur.rowcount} rows in vlm_no_results table.")

    conn.commit()
    print("Cleanup complete!")
    conn.close()

if __name__ == "__main__":
    cleanup()
