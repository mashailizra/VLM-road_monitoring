"""
routes/ingest.py — POST endpoints that receive data from the Colab pipeline.

  POST /yolo-inference  — save a YOLO detection
  POST /vlm-no          — save a VLM rejection

Images are stored as base64 strings directly in the database.
"""

import os
import base64
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify

from database import insert_detection, insert_vlm_yes, insert_vlm_no
from utils import save_image

ingest_bp = Blueprint("ingest", __name__)


# ──────────────────────────────────────────────────────────────
# POST /yolo-inference
# ──────────────────────────────────────────────────────────────
@ingest_bp.route("/yolo-inference", methods=["POST"])
def yolo_inference():
    """
    Expected JSON:
      { "defect_type": "pothole", "confidence": 0.87,
        "model_name": "yolov8n", "image": "<base64 JPEG>",
        "status": "accepted" | "rejected" }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "msg": "no JSON body"}), 400

    defect_type = data.get("defect_type")
    confidence  = data.get("confidence")
    status      = data.get("status", "accepted") # Default to accepted

    if not defect_type or confidence is None:
        return jsonify({"status": "error", "msg": "defect_type and confidence are required"}), 400

    # Save image to disk
    image_path = save_image(data.get("image"), "live_history/yolo_detect", status)

    # ONLY store in detections table if confidence >= 0.80 (Auto-Accepted)
    # 0.30 - 0.80 is handled by VLM routes. < 0.30 is discarded.
    if confidence < 0.80:
        return jsonify({
            "status": "ignored", 
            "msg": f"Confidence {confidence} < 0.80. Not stored in YOLO detections table.",
            "image_path": image_path
        }), 200

    detection_id = insert_detection(
        defect_type=defect_type,
        confidence=confidence,
        model_name=data.get("model_name"),
        image_path=image_path,
        track_id=data.get("track_id"),
        status="accepted" # Always accepted if > 0.80
    )
    return jsonify({"status": "ok", "detection_id": detection_id, "image_path": image_path}), 201


# ──────────────────────────────────────────────────────────────
# POST /vlm-yes
# ──────────────────────────────────────────────────────────────
@ingest_bp.route("/vlm-yes", methods=["POST"])
def vlm_yes():
    """
    Expected JSON:
      { "defect_type": "pothole", "model": "gemini-1.5-flash",
        "image": "<base64 JPEG>" }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "msg": "no JSON body"}), 400

    image_path = save_image(data.get("image"), "live_history/vlm_detect", "vlm_yes")

    vlm_id = insert_vlm_yes(
        defect_type=data.get("defect_type"),
        image_path=image_path,
        model=data.get("model"),
        reasoning=data.get("reasoning"),
        track_id=data.get("track_id")
    )
    return jsonify({"status": "ok", "vlm_id": vlm_id, "image_path": image_path}), 201


# ──────────────────────────────────────────────────────────────
# POST /vlm-no
# ──────────────────────────────────────────────────────────────
@ingest_bp.route("/vlm-no", methods=["POST"])
def vlm_no():
    """
    Expected JSON:
      { "defect_type": "pothole", "model": "gemini-1.5-flash",
        "reasoning": "not a real defect", "image": "<base64 JPEG>" }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "msg": "no JSON body"}), 400

    image_path = save_image(data.get("image"), "live_history/vlm_detect", "vlm_no")

    vlm_no_id = insert_vlm_no(
        defect_type=data.get("defect_type"),
        image_path=image_path,
        model=data.get("model"),
        reasoning=data.get("reasoning"),
        track_id=data.get("track_id"),
    )
    return jsonify({"status": "ok", "vlm_no_id": vlm_no_id, "image_path": image_path}), 201
