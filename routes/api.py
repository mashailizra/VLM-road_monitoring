"""
routes/api.py — Read-only JSON endpoints used by the dashboard frontend.

  GET /api/detections       — list YOLO detections (with filters)
  GET /api/vlm-no           — list VLM rejections (with filters)
  GET /api/stats            — aggregate counts
  GET /api/image/<path>     — serve a stored image file
"""

import os

from flask import Blueprint, request, jsonify, send_from_directory, abort, render_template

from database import query_detections, query_vlm_no, get_stats_from_db

api_bp = Blueprint("api", __name__)

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images")


@api_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@api_bp.route("/api/detections")
def get_detections():
    rows = query_detections(
        defect_type=request.args.get("defect_type"),
        start=request.args.get("start"),
        end=request.args.get("end"),
        limit=request.args.get("limit", 200),
    )
    return jsonify(rows)


@api_bp.route("/api/vlm-no")
def get_vlm_no():
    rows = query_vlm_no(
        model=request.args.get("model"),
        start=request.args.get("start"),
        end=request.args.get("end"),
        limit=request.args.get("limit", 200),
    )
    return jsonify(rows)


@api_bp.route("/api/stats")
def get_stats():
    return jsonify(get_stats_from_db())


@api_bp.route("/api/image/<path:filename>")
def serve_image(filename):
    # Guard against path traversal
    safe_path = os.path.normpath(filename)
    if safe_path.startswith(".."):
        abort(400)
    return send_from_directory(IMAGES_DIR, safe_path)
