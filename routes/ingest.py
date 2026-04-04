"""
routes/ingest.py — POST endpoints that receive data from the Colab pipeline.

  POST /yolo-inference  — save a YOLO detection
  POST /vlm-no          — save a VLM rejection

Images are stored as base64 strings directly in the database.
"""

from flask import Blueprint, request, jsonify

from database import insert_detection, insert_vlm_no

ingest_bp = Blueprint("ingest", __name__)


def _clean_b64(b64_string: str) -> str:
    """Strip data URI prefix if present, e.g. 'data:image/jpeg;base64,...'"""
    if b64_string and "base64," in b64_string:
        return b64_string.split("base64,", 1)[1]
    return b64_string


# ──────────────────────────────────────────────────────────────
# POST /yolo-inference
# ──────────────────────────────────────────────────────────────
@ingest_bp.route("/yolo-inference", methods=["POST"])
def yolo_inference():
    """
    Expected JSON:
      { "defect_type": "pothole", "confidence": 0.87,
        "model_name": "yolov8n", "image": "<base64 JPEG>" }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "msg": "no JSON body"}), 400

    defect_type = data.get("defect_type")
    confidence  = data.get("confidence")

    if not defect_type or confidence is None:
        return jsonify({"status": "error", "msg": "defect_type and confidence are required"}), 400

    detection_id = insert_detection(
        defect_type=defect_type,
        confidence=confidence,
        model_name=data.get("model_name"),
        image=_clean_b64(data.get("image")),   # stored as clean base64 in DB
    )
    return jsonify({"status": "ok", "detection_id": detection_id}), 201


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

    vlm_no_id = insert_vlm_no(
        defect_type=data.get("defect_type"),
        image=_clean_b64(data.get("image")),   # stored as clean base64 in DB
        model=data.get("model"),
        reasoning=data.get("reasoning"),
    )
    return jsonify({"status": "ok", "vlm_no_id": vlm_no_id}), 201
