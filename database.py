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
                image        TEXT
            );

            CREATE TABLE IF NOT EXISTS vlm_no_results (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                defect_type  TEXT,
                image        TEXT,
                timestamp    TEXT NOT NULL DEFAULT (datetime('now')),
                model        TEXT,
                reasoning    TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_detections_type ON detections(defect_type);
            CREATE INDEX IF NOT EXISTS idx_detections_ts   ON detections(timestamp);
            CREATE INDEX IF NOT EXISTS idx_vlm_no_ts       ON vlm_no_results(timestamp);
        """)


def insert_detection(defect_type, confidence, model_name=None, image=None) -> int:
    """Insert a YOLO detection row. Returns the new row id."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO detections (defect_type, confidence, model_name, image)
               VALUES (?, ?, ?, ?)""",
            (defect_type, float(confidence), model_name, image),
        )
        return cur.lastrowid


def insert_vlm_no(defect_type=None, image=None, model=None, reasoning=None) -> int:
    """Insert a VLM rejection row. Returns the new row id."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO vlm_no_results (defect_type, image, model, reasoning)
               VALUES (?, ?, ?, ?)""",
            (defect_type, image, model, reasoning),
        )
        return cur.lastrowid


def query_detections(defect_type=None, start=None, end=None, limit=200) -> list:
    """Return detections as a list of dicts, newest first."""
    sql = "SELECT * FROM detections WHERE 1=1"
    params = []
    if defect_type:
        sql += " AND defect_type = ?"
        params.append(defect_type)
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


def get_stats_from_db() -> dict:
    """Return aggregate counts used by the dashboard stats cards."""
    with get_db() as conn:
        total_detections = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
        vlm_no_count     = conn.execute("SELECT COUNT(*) FROM vlm_no_results").fetchone()[0]
        model_rows       = conn.execute(
            "SELECT DISTINCT model_name FROM detections WHERE model_name IS NOT NULL"
        ).fetchall()
        models = [r[0] for r in model_rows]
    return {
        "total_detections": total_detections,
        "vlm_no_count": vlm_no_count,
        "models": models,
    }
