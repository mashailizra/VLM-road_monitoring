import sqlite3

def migrate():
    conn = sqlite3.connect('detections.db')
    cur = conn.cursor()
    
    # Add reasoning to vlm_detections
    try:
        cur.execute('ALTER TABLE vlm_detections ADD COLUMN reasoning TEXT')
        print("Added 'reasoning' column to vlm_detections table.")
    except sqlite3.OperationalError:
        print("Column 'reasoning' already exists in vlm_detections or table not found.")

    # Add reasoning to live_feed_history
    try:
        cur.execute('ALTER TABLE live_feed_history ADD COLUMN reasoning TEXT')
        print("Added 'reasoning' column to live_feed_history table.")
    except sqlite3.OperationalError:
        print("Column 'reasoning' already exists in live_feed_history or table not found.")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
