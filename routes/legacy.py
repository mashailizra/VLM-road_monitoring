"""
routes/legacy.py — Legacy Colab pipeline compatibility routes.

  POST /ingest
  GET  /api/live
  GET  /api/frame/<frame_name>/<track_id>/<route>
  GET  /img/<path>
  GET  /live  (redirects to /dashboard)
"""

import os, base64, time
from collections import deque
from threading import Lock

from flask import (Blueprint, send_file, jsonify, abort,
                   request, Response, redirect)
from dotenv import load_dotenv

load_dotenv()

legacy_bp = Blueprint("legacy", __name__)

OUTPUT_ROOT = os.getenv("OUTPUT_ROOT", "")

# ── Live feed state (in-memory, thread-safe) ──────────────────
LIVE_MAX      = 200
live_feed     = deque(maxlen=LIVE_MAX)
live_lock     = Lock()
live_counters = {
    "total": 0, "accepted": 0, "rejected": 0,
    "vlm_called": 0, "cached": 0,
}


# ── Routes ────────────────────────────────────────────────────

@legacy_bp.route("/img/<path:rel>")
def serve_img(rel):
    full = os.path.join(OUTPUT_ROOT, rel)
    if not os.path.isfile(full):
        abort(404)
    return send_file(full)


@legacy_bp.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "msg": "no JSON"}), 400

    route = data.get("route", "")

    with live_lock:
        data["received_at"] = time.time()
        live_feed.appendleft(data)

        live_counters["total"] += 1
        if "ACCEPT" in route:
            live_counters["accepted"] += 1
        if "REJECT" in route or "NO" in route:
            live_counters["rejected"] += 1
        if route in ("VLM-YES", "VLM-NO"):
            live_counters["vlm_called"] += 1
        if "CACHED" in route:
            live_counters["cached"] += 1

    return jsonify({"status": "ok"}), 200


@legacy_bp.route("/api/live")
def api_live():
    limit = int(request.args.get("limit", 40))
    with live_lock:
        items = list(live_feed)[:limit]
        ctrs  = dict(live_counters)
    slim = [{k: v for k, v in item.items() if k != "frame_b64"} for item in items]
    return jsonify({"counters": ctrs, "items": slim})


@legacy_bp.route("/api/frame/<frame_name>/<int:track_id>/<route>")
def api_frame(frame_name, track_id, route):
    with live_lock:
        for item in live_feed:
            if (item.get("frame_name") == frame_name
                    and item.get("track_id") == track_id
                    and item.get("route") == route):
                b64 = item.get("frame_b64")
                if b64:
                    img_bytes = base64.b64decode(b64)
                    return Response(img_bytes, mimetype="image/jpeg")
    abort(404)


@legacy_bp.route("/live")
def live():
    return redirect("/dashboard")
