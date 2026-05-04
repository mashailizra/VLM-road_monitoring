"""
database.py — SQLite helpers for the VLM Dashboard.

Tables (schema from CLAUDE.md):
  detections     — YOLO inference results
  vlm_no_results — VLM rejection results
"""

import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "detections.db")


def get_db():
    """Open a SQLite connection with dict-like row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and indexes if they don't exist yet."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS detections (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                defect_type  TEXT    NOT NULL,
                confidence   REAL    NOT NULL,
                timestamp    TEXT    NOT NULL DEFAULT (datetime('now')),
                model_name   TEXT,
                image        TEXT,
                track_id     INTEGER,
                status       TEXT    DEFAULT 'accepted'
            );

            CREATE TABLE IF NOT EXISTS vlm_detections (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                defect_type  TEXT,
                image        TEXT,
                timestamp    TEXT NOT NULL DEFAULT (datetime('now')),
                model        TEXT,
                reasoning    TEXT,
                track_id     INTEGER
            );

            CREATE TABLE IF NOT EXISTS vlm_no_results (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                defect_type  TEXT,
                image        TEXT,
                timestamp    TEXT NOT NULL DEFAULT (datetime('now')),
                model        TEXT,
                reasoning    TEXT,
                track_id     INTEGER
            );

            CREATE TABLE IF NOT EXISTS live_feed_history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                route        TEXT,
                label        TEXT,
                confidence   REAL,
                track_id     INTEGER,
                image        TEXT,
                timestamp    TEXT NOT NULL DEFAULT (datetime('now')),
                reasoning    TEXT,
                meta_json    TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_detections_type ON detections(defect_type);
            CREATE INDEX IF NOT EXISTS idx_detections_ts   ON detections(timestamp);
            CREATE INDEX IF NOT EXISTS idx_vlm_ts          ON vlm_detections(timestamp);
            CREATE INDEX IF NOT EXISTS idx_vlm_no_ts       ON vlm_no_results(timestamp);
            CREATE INDEX IF NOT EXISTS idx_live_ts         ON live_feed_history(timestamp);
        """)


def insert_detection(defect_type, confidence, model_name=None, image_path=None, track_id=None, status='accepted') -> int:
    """Insert a YOLO detection row. image_path is relative to static/."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO detections (defect_type, confidence, model_name, image, track_id, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (defect_type, float(confidence), model_name, image_path, track_id, status),
        )
        return cur.lastrowid


def insert_vlm_yes(defect_type=None, image_path=None, model=None, reasoning=None, track_id=None) -> int:
    """Insert a VLM confirmation row. image_path is relative to static/."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO vlm_detections (defect_type, image, model, reasoning, track_id)
               VALUES (?, ?, ?, ?, ?)""",
            (defect_type, image_path, model, reasoning, track_id),
        )
        return cur.lastrowid


def insert_vlm_no(defect_type=None, image_path=None, model=None, reasoning=None, track_id=None) -> int:
    """Insert a VLM rejection row. image_path is relative to static/."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO vlm_no_results (defect_type, image, model, reasoning, track_id)
               VALUES (?, ?, ?, ?, ?)""",
            (defect_type, image_path, model, reasoning, track_id),
        )
        return cur.lastrowid


def query_detections(defect_type=None, status=None, start=None, end=None, limit=200) -> list:
    """Return detections as a list of dicts, newest first."""
    sql = "SELECT * FROM detections WHERE 1=1"
    params = []
    if defect_type:
        sql += " AND defect_type = ?"
        params.append(defect_type)
    if status:
        sql += " AND status = ?"
        params.append(status)
    if start:
        sql += " AND timestamp >= ?"
        params.append(start)
    if end:
        sql += " AND timestamp <= ?"
        params.append(end)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(int(limit))

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def query_vlm_yes(defect_type=None, model=None, start=None, end=None, limit=200) -> list:
    """Return VLM confirmations as a list of dicts."""
    sql = "SELECT * FROM vlm_detections WHERE 1=1"
    params = []
    if defect_type:
        sql += " AND defect_type = ?"
        params.append(defect_type)
    if model:
        sql += " AND model = ?"
        params.append(model)
    if start:
        sql += " AND timestamp >= ?"
        params.append(start)
    if end:
        sql += " AND timestamp <= ?"
        params.append(end)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(int(limit))

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def query_vlm_no(model=None, start=None, end=None, limit=200) -> list:
    """Return VLM rejections as a list of dicts, newest first."""
    sql = "SELECT * FROM vlm_no_results WHERE 1=1"
    params = []
    if model:
        sql += " AND model = ?"
        params.append(model)
    if start:
        sql += " AND timestamp >= ?"
        params.append(start)
    if end:
        sql += " AND timestamp <= ?"
        params.append(end)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(int(limit))

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def insert_live_history(route=None, label=None, confidence=None, track_id=None, image_path=None, reasoning=None, meta_json=None) -> int:
    """Insert a persistent record of a live feed event."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO live_feed_history (route, label, confidence, track_id, image, reasoning, meta_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (route, label, confidence, track_id, image_path, reasoning, meta_json),
        )
        return cur.lastrowid


def query_live_history(limit=100) -> list:
    """Return recent live history items."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM live_feed_history ORDER BY id DESC LIMIT ?",
            (int(limit),)
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats_from_db() -> dict:
    """Return aggregate counts used by the dashboard stats cards."""
    with get_db() as conn:
        total_detections = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
        vlm_yes_count    = conn.execute("SELECT COUNT(*) FROM vlm_detections").fetchone()[0]
        vlm_no_count     = conn.execute("SELECT COUNT(*) FROM vlm_no_results").fetchone()[0]
        model_rows       = conn.execute(
            "SELECT DISTINCT model_name FROM detections WHERE model_name IS NOT NULL"
        ).fetchall()
        models = [r[0] for r in model_rows]
    return {
        "total_detections": total_detections,
        "vlm_yes_count": vlm_yes_count,
        "vlm_no_count": vlm_no_count,
        "models": models,
    }
