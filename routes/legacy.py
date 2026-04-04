"""
routes/legacy.py — All original routes from app.py, preserved unchanged.

Existing Colab pipeline compatibility:
  POST /ingest
  GET  /api/live
  GET  /api/frame/<frame_name>/<track_id>/<route>
  GET  /img/<path>
  GET  /          (overview)
  GET  /live
  GET  /accepted
  GET  /rejected
  GET  /reasoning
  GET  /visualizations
  GET  /tracking
"""

import os, json, glob, base64, time
from pathlib import Path
from collections import deque
from threading import Lock

from flask import (Blueprint, render_template_string, send_file,
                   jsonify, abort, request, Response)
from dotenv import load_dotenv

load_dotenv()

legacy_bp = Blueprint("legacy", __name__)

OUTPUT_ROOT      = os.getenv("OUTPUT_ROOT", "")
ACCEPTED_IMG_DIR = os.path.join(OUTPUT_ROOT, "accepted", "images")
ACCEPTED_LBL_DIR = os.path.join(OUTPUT_ROOT, "accepted", "labels")
REJECTED_IMG_DIR = os.path.join(OUTPUT_ROOT, "rejected", "images")
REJECTED_LBL_DIR = os.path.join(OUTPUT_ROOT, "rejected", "labels")
REJECTED_LOG_DIR = os.path.join(OUTPUT_ROOT, "rejected", "reasoning")
VIS_DIR          = os.path.join(OUTPUT_ROOT, "visualizations")
TRACKING_DIR     = os.path.join(VIS_DIR, "tracking_frames")

IMG_EXTS = {".jpg", ".jpeg", ".png"}

# ── Live feed state (in-memory, thread-safe) ──────────────────
LIVE_MAX      = 200
live_feed     = deque(maxlen=LIVE_MAX)
live_lock     = Lock()
live_counters = {
    "total": 0, "accepted": 0, "rejected": 0,
    "vlm_called": 0, "cached": 0,
}

ROUTE_COLORS = {
    "AUTO-ACCEPT"    : "#34d399",
    "VLM-YES"        : "#4ade80",
    "CACHED-ACCEPT"  : "#60a5fa",
    "LOW-CONF REJECT": "#94a3b8",
    "VLM-NO"         : "#f87171",
    "CACHED-REJECT"  : "#c084fc",
}

# ── Shared CSS & helpers ──────────────────────────────────────
BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e2e8f0; }

.sidebar {
    width: 220px; min-height: 100vh; background: #1a1d27;
    position: fixed; top: 0; left: 0;
    border-right: 1px solid #2d3148; z-index: 100;
    display: flex; flex-direction: column;
}
.sidebar .logo {
    padding: 22px 18px 18px; font-size: 15px; font-weight: 700;
    color: #818cf8; border-bottom: 1px solid #2d3148; line-height: 1.4;
}
.sidebar .logo span { color: #e2e8f0; }
.sidebar nav { padding: 12px 0; flex: 1; }
.sidebar nav a {
    display: flex; align-items: center; gap: 10px;
    padding: 11px 20px; color: #94a3b8; text-decoration: none;
    font-size: 13.5px; transition: all .18s;
}
.sidebar nav a:hover, .sidebar nav a.active {
    background: #252840; color: #818cf8;
    border-left: 3px solid #818cf8;
}
.sidebar nav a .ico { font-size: 16px; width: 20px; text-align: center; }
.sidebar .version { padding: 14px 18px; font-size: 11px; color: #475569;
    border-top: 1px solid #2d3148; }

.main { margin-left: 220px; padding: 28px 32px; min-height: 100vh; }
.page-title { font-size: 22px; font-weight: 700; color: #e2e8f0; margin-bottom: 6px; }
.page-sub { font-size: 13px; color: #64748b; margin-bottom: 26px; }

.cards { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 28px; }
.card { background: #1a1d27; border: 1px solid #2d3148; border-radius: 12px; padding: 20px 22px; }
.card .label { font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: .06em; }
.card .value { font-size: 30px; font-weight: 700; margin: 4px 0 2px; }
.card .sub   { font-size: 12px; color: #64748b; }
.card.green  .value { color: #34d399; }
.card.red    .value { color: #f87171; }
.card.blue   .value { color: #60a5fa; }
.card.purple .value { color: #a78bfa; }
.card.orange .value { color: #fb923c; }

.section { margin-bottom: 32px; }
.section-title {
    font-size: 15px; font-weight: 600; color: #cbd5e1;
    margin-bottom: 14px; padding-bottom: 8px;
    border-bottom: 1px solid #2d3148;
}

.img-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px,1fr)); gap: 14px; }
.img-card {
    background: #1a1d27; border: 1px solid #2d3148;
    border-radius: 10px; overflow: hidden; cursor: pointer;
    transition: transform .18s, border-color .18s;
}
.img-card:hover { transform: translateY(-3px); border-color: #818cf8; }
.img-card img { width: 100%; height: 160px; object-fit: cover; display: block; }
.img-card .img-info { padding: 8px 10px; font-size: 11.5px; color: #94a3b8;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.img-badge { display: inline-block; padding: 1px 7px; border-radius: 20px;
    font-size: 10px; font-weight: 600; margin-bottom: 3px; }
.badge-acc  { background: #064e3b; color: #34d399; }
.badge-rej  { background: #450a0a; color: #f87171; }
.badge-vlm  { background: #1e1b4b; color: #a78bfa; }
.badge-auto { background: #052e16; color: #4ade80; }

.chart-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(460px,1fr)); gap: 18px; }
.chart-card { background: #1a1d27; border: 1px solid #2d3148; border-radius: 12px; overflow: hidden; }
.chart-card img { width: 100%; display: block; }
.chart-card .chart-label { padding: 8px 14px; font-size: 12px; color: #64748b;
    border-top: 1px solid #2d3148; }

.reason-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.reason-table th { text-align: left; padding: 10px 14px; background: #1e2235;
    color: #64748b; font-weight: 600; border-bottom: 1px solid #2d3148; }
.reason-table td { padding: 10px 14px; border-bottom: 1px solid #1e2235; vertical-align: top; }
.reason-table tr:hover td { background: #1e2235; }
.reason-table .reason-text { color: #94a3b8; font-style: italic; }

.class-row { display: flex; align-items: center; gap: 14px; margin-bottom: 10px; }
.class-row .cls-name { width: 70px; font-size: 13px; color: #94a3b8; }
.cls-bar-wrap { flex: 1; background: #2d3148; border-radius: 4px; height: 8px; }
.cls-bar { height: 8px; border-radius: 4px; }
.cls-crack   { background: #60a5fa; }
.cls-pothole { background: #f472b6; }
.class-row .cls-count { width: 40px; text-align: right; font-size: 13px; font-weight: 600; }

.modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.85);
    z-index: 1000; align-items: center; justify-content: center; }
.modal-overlay.open { display: flex; }
.modal-box { background: #1a1d27; border: 1px solid #2d3148; border-radius: 14px;
    max-width: 90vw; max-height: 90vh; overflow: auto; padding: 20px; position: relative; }
.modal-close { position: absolute; top: 12px; right: 14px; background: none;
    border: none; color: #64748b; font-size: 22px; cursor: pointer; }
.modal-close:hover { color: #e2e8f0; }
.modal-img { max-width: 100%; max-height: 70vh; display: block; margin: 0 auto 14px; }
.modal-meta { font-size: 13px; color: #94a3b8; }

.empty { text-align: center; padding: 60px 20px; color: #475569; font-size: 14px; }
.empty .ico { font-size: 40px; margin-bottom: 10px; }

.pagination { display: flex; gap: 8px; margin-top: 18px; align-items: center; justify-content: center; }
.pagination button { background: #1e2235; border: 1px solid #2d3148; color: #94a3b8;
    padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.pagination button:hover { background: #818cf8; color: #fff; border-color: #818cf8; }

.live-header { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; }
.live-dot { width: 10px; height: 10px; border-radius: 50%; background: #34d399;
    animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
.live-status { font-size: 13px; color: #64748b; }

.det-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px,1fr)); gap: 14px; }
.det-card { background: #1a1d27; border: 1px solid #2d3148; border-radius: 12px;
    overflow: hidden; transition: border-color .2s; }
.det-card:hover { border-color: #818cf8; }
.det-card img { width: 100%; height: 150px; object-fit: cover; display: block; cursor: pointer; }
.det-body { padding: 10px 12px; }
.det-route { font-size: 11px; font-weight: 700; padding: 2px 8px;
    border-radius: 20px; display: inline-block; margin-bottom: 6px; }
.det-meta { font-size: 12px; color: #64748b; line-height: 1.6; }
.det-reason { font-size: 11.5px; color: #f87171; margin-top: 4px; font-style: italic; }
"""

NAV_LINKS = [
    ("Overview",       "/",              "📊"),
    ("Dashboard",      "/dashboard",     "🗃️"),
    ("Live Feed",      "/live",          "📡"),
    ("Accepted",       "/accepted",      "✅"),
    ("Rejected",       "/rejected",      "❌"),
    ("Reasoning",      "/reasoning",     "🧠"),
    ("Visualizations", "/visualizations","📈"),
    ("Tracking",       "/tracking",      "🎯"),
]

MODAL_JS = """
function openImg(src, meta) {
  document.getElementById('modal-img').src = src;
  document.getElementById('modal-meta').textContent = meta || '';
  document.getElementById('modal').classList.add('open');
}
function closeModal(e) {
  if (e.target === document.getElementById('modal'))
    document.getElementById('modal').classList.remove('open');
}
"""

PAGER_JS = """
function initPager(gridId, pageSize) {
  const grid = document.getElementById(gridId);
  if (!grid) return;
  const cards = [...grid.children];
  let cur = 0;
  const pages = Math.ceil(cards.length / pageSize);
  const pg = document.getElementById(gridId + '-pg');
  if (!pg) return;
  function render() {
    cards.forEach((c,i) => c.style.display = (i>=cur*pageSize && i<(cur+1)*pageSize)?'':'none');
    pg.innerHTML = '';
    if (pages <= 1) return;
    const prev = document.createElement('button');
    prev.textContent = '← Prev';
    prev.onclick = () => { if(cur>0){cur--;render();} };
    pg.appendChild(prev);
    const info = document.createElement('span');
    info.textContent = `Page ${cur+1} of ${pages}`;
    info.style.cssText = 'color:#64748b;font-size:13px';
    pg.appendChild(info);
    const next = document.createElement('button');
    next.textContent = 'Next →';
    next.onclick = () => { if(cur<pages-1){cur++;render();} };
    pg.appendChild(next);
  }
  render();
}
window.addEventListener('DOMContentLoaded', () => {
  initPager('acc-grid', 24);
  initPager('rej-grid', 24);
  initPager('track-grid', 18);
});
"""


def nav_html(active_path):
    links = ""
    for label, href, ico in NAV_LINKS:
        cls = 'active' if href == active_path else ''
        links += f'<a href="{href}" class="{cls}"><span class="ico">{ico}</span>{label}</a>\n'
    return f'''<div class="sidebar">
      <div class="logo">🛣️ Road Defect<br><span>Dashboard</span></div>
      <nav>{links}</nav>
      <div class="version">YOLO + VLM + ngrok</div>
    </div>'''


def page(title, subtitle, body, active_path="/", extra_js=""):
    return render_template_string(f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} — Road Defect Dashboard</title>
<style>{BASE_CSS}</style>
</head><body>
{nav_html(active_path)}
<div class="main">
  <div class="page-title">{title}</div>
  <div class="page-sub">{subtitle}</div>
  {body}
</div>
<div class="modal-overlay" id="modal" onclick="closeModal(event)">
  <div class="modal-box">
    <button class="modal-close" onclick="document.getElementById('modal').classList.remove('open')">✕</button>
    <img class="modal-img" id="modal-img" src="" alt="">
    <div class="modal-meta" id="modal-meta"></div>
  </div>
</div>
<script>{MODAL_JS}{PAGER_JS}{extra_js}</script>
</body></html>""")


def list_images(folder):
    if not os.path.exists(folder):
        return []
    return sorted(f for f in os.listdir(folder)
                  if Path(f).suffix.lower() in IMG_EXTS)


def load_all_reasoning():
    data = {}
    if not os.path.exists(REJECTED_LOG_DIR):
        return data
    for jf in sorted(glob.glob(os.path.join(REJECTED_LOG_DIR, "*.json"))):
        try:
            with open(jf) as f:
                data[Path(jf).stem] = json.load(f)
        except Exception:
            pass
    return data


def count_labels(label_dir):
    counts = {"crack": 0, "pothole": 0}
    if not os.path.exists(label_dir):
        return counts
    for fname in os.listdir(label_dir):
        if not fname.endswith(".txt"):
            continue
        try:
            with open(os.path.join(label_dir, fname)) as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        cls_name = {0: "crack", 1: "pothole"}.get(int(parts[0]), "unknown")
                        counts[cls_name] = counts.get(cls_name, 0) + 1
        except Exception:
            pass
    return counts


def get_stats():
    acc_imgs      = list_images(ACCEPTED_IMG_DIR)
    rej_imgs      = list_images(REJECTED_IMG_DIR)
    acc_labels    = count_labels(ACCEPTED_LBL_DIR)
    rej_labels    = count_labels(REJECTED_LBL_DIR)
    reasoning     = load_all_reasoning()
    vis_charts    = [f for f in os.listdir(VIS_DIR)
                     if Path(f).suffix.lower() in {".png", ".jpg"}
                     and os.path.isfile(os.path.join(VIS_DIR, f))] \
                    if os.path.exists(VIS_DIR) else []
    tracking_imgs = list_images(TRACKING_DIR)
    total_acc     = acc_labels["crack"] + acc_labels["pothole"]
    total_rej     = rej_labels["crack"] + rej_labels["pothole"]
    return {
        "accepted_images" : acc_imgs,
        "rejected_images" : rej_imgs,
        "acc_labels"      : acc_labels,
        "rej_labels"      : rej_labels,
        "total_accepted"  : total_acc,
        "total_rejected"  : total_rej,
        "total_detections": total_acc + total_rej,
        "vlm_rejected"    : sum(len(v) for v in reasoning.values()),
        "reasoning"       : reasoning,
        "vis_charts"      : sorted(vis_charts),
        "tracking_imgs"   : tracking_imgs,
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


@legacy_bp.route("/")
def overview():
    s = get_stats()
    total = s["total_detections"] or 1
    acc_rate = round(s["total_accepted"] / total * 100, 1)

    with live_lock:
        live_total = live_counters["total"]

    def bar(count, max_count, cls):
        pct = int(count / max(max_count, 1) * 100)
        return f"""<div class="class-row">
          <div class="cls-name">{cls.capitalize()}</div>
          <div class="cls-bar-wrap"><div class="cls-bar cls-{cls}" style="width:{pct}%"></div></div>
          <div class="cls-count">{count}</div>
        </div>"""

    ac, ap = s["acc_labels"]["crack"], s["acc_labels"]["pothole"]
    rc, rp = s["rej_labels"]["crack"], s["rej_labels"]["pothole"]
    mx     = max(ac, ap, rc, rp, 1)

    body = f"""
    <div class="cards">
      <div class="card blue">
        <div class="label">Disk Detections</div>
        <div class="value">{s['total_detections']}</div>
        <div class="sub">saved to output folder</div>
      </div>
      <div class="card green">
        <div class="label">Accepted</div>
        <div class="value">{s['total_accepted']}</div>
        <div class="sub">{acc_rate}% acceptance rate</div>
      </div>
      <div class="card red">
        <div class="label">Rejected</div>
        <div class="value">{s['total_rejected']}</div>
        <div class="sub">low-conf + VLM-NO</div>
      </div>
      <div class="card purple">
        <div class="label">Live Received</div>
        <div class="value">{live_total}</div>
        <div class="sub">via ngrok POST</div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:28px">
      <div class="card">
        <div class="section-title">✅ Accepted by Class</div>
        {bar(ac, mx, 'crack')}{bar(ap, mx, 'pothole')}
      </div>
      <div class="card">
        <div class="section-title">❌ Rejected by Class</div>
        {bar(rc, mx, 'crack')}{bar(rp, mx, 'pothole')}
      </div>
    </div>

    <div class="section">
      <div class="section-title">📂 Output Folder</div>
      <div class="card">
        <table class="reason-table">
          <tr><th>Folder</th><th>Count</th></tr>
          <tr><td>accepted/images/</td><td>{len(s['accepted_images'])} frames</td></tr>
          <tr><td>accepted/labels/</td><td>{ac+ap} detections</td></tr>
          <tr><td>rejected/images/</td><td>{len(s['rejected_images'])} frames</td></tr>
          <tr><td>rejected/reasoning/</td><td>{len(s['reasoning'])} JSON files</td></tr>
          <tr><td>visualizations/</td><td>{len(s['vis_charts'])} charts</td></tr>
          <tr><td>visualizations/tracking_frames/</td><td>{len(s['tracking_imgs'])} frames</td></tr>
        </table>
      </div>
    </div>"""
    return page("Overview", "Pipeline results summary", body, "/")


@legacy_bp.route("/accepted")
def accepted():
    imgs = list_images(ACCEPTED_IMG_DIR)
    if not imgs:
        body = '<div class="empty"><div class="ico">📭</div>No accepted frames yet.</div>'
    else:
        cards = "".join(f"""
        <div class="img-card" onclick="openImg('/img/accepted/images/{f}','{f}')">
          <img src="/img/accepted/images/{f}" loading="lazy" alt="{f}">
          <div class="img-info"><span class="img-badge badge-acc">ACCEPTED</span><br>{f}</div>
        </div>""" for f in imgs)
        body = f"""<div class="section">
          <div class="section-title">✅ Accepted Frames — {len(imgs)} images</div>
          <div class="img-grid" id="acc-grid">{cards}</div>
          <div class="pagination" id="acc-grid-pg"></div>
        </div>"""
    return page("Accepted Detections",
                f"{len(imgs)} frames with confirmed defects",
                body, "/accepted")


@legacy_bp.route("/rejected")
def rejected():
    imgs = list_images(REJECTED_IMG_DIR)
    if not imgs:
        body = '<div class="empty"><div class="ico">📭</div>No rejected frames yet.</div>'
    else:
        def badge(fname):
            if "vlm" in fname.lower(): return "badge-vlm", "VLM-NO"
            return "badge-rej", "LOW-CONF"
        cards = "".join(f"""
        <div class="img-card" onclick="openImg('/img/rejected/images/{f}','{f}')">
          <img src="/img/rejected/images/{f}" loading="lazy" alt="{f}">
          <div class="img-info">
            <span class="img-badge {badge(f)[0]}">{badge(f)[1]}</span><br>{f}
          </div>
        </div>""" for f in imgs)
        body = f"""<div class="section">
          <div class="section-title">❌ Rejected Frames — {len(imgs)} images</div>
          <div class="img-grid" id="rej-grid">{cards}</div>
          <div class="pagination" id="rej-grid-pg"></div>
        </div>"""
    return page("Rejected Detections",
                f"{len(imgs)} rejected frames",
                body, "/rejected")


@legacy_bp.route("/reasoning")
def reasoning():
    data = load_all_reasoning()
    if not data:
        body = '<div class="empty"><div class="ico">🧠</div>No reasoning files yet.</div>'
    else:
        rows = ""
        for stem, entries in sorted(data.items()):
            for e in entries:
                conf     = e.get("confidence", 0)
                conf_col = "#f87171" if conf < 0.3 else "#fb923c"
                reason   = e.get("vlm_reason", "—")
                thinking = e.get("vlm_thinking", "")
                think_td = (f'<details><summary style="cursor:pointer;color:#60a5fa;font-size:12px">'
                            f'Show thinking</summary><div style="color:#64748b;font-size:12px;'
                            f'white-space:pre-wrap;margin-top:6px">{thinking[:600]}</div></details>'
                            if thinking else "—")
                rows += f"""<tr>
                  <td><code style="font-size:11px;color:#94a3b8">{e.get('frame', stem)}</code></td>
                  <td><b style="color:#a78bfa">#{e.get('track_id', '—')}</b></td>
                  <td>{e.get('yolo_class', '—')}</td>
                  <td><span style="color:{conf_col};font-weight:700">{conf:.3f}</span></td>
                  <td class="reason-text">{reason}</td>
                  <td>{think_td}</td>
                </tr>"""
        total = sum(len(v) for v in data.values())
        body = f"""<div class="section">
          <div class="section-title">🧠 VLM Rejection Reasoning — {total} entries</div>
          <div class="card" style="overflow-x:auto">
            <table class="reason-table">
              <thead><tr><th>Frame</th><th>Track ID</th><th>Class</th>
                <th>Confidence</th><th>VLM Reason</th><th>Thinking</th></tr></thead>
              <tbody>{rows}</tbody>
            </table>
          </div>
        </div>"""
    return page("VLM Reasoning", "Why each detection was rejected", body, "/reasoning")


@legacy_bp.route("/visualizations")
def visualizations():
    charts = sorted(f for f in os.listdir(VIS_DIR)
                    if Path(f).suffix.lower() in {".png", ".jpg"}
                    and os.path.isfile(os.path.join(VIS_DIR, f))) \
             if os.path.exists(VIS_DIR) else []
    LABELS = {
        "routing_breakdown.png"           : "Detection Routing Breakdown",
        "confidence_distributions.png"    : "Confidence Distributions",
        "sample_accepted.png"             : "Sample Accepted Detections",
        "sample_rejected.png"             : "Sample Rejected Detections",
        "accepted_vs_rejected_by_class.png": "Accepted vs Rejected by Class",
        "yolo_tracking_grid.png"          : "YOLO Tracking Grid",
        "yolo_tracking_stats.png"         : "Tracking Statistics",
    }
    if not charts:
        body = '<div class="empty"><div class="ico">📈</div>No charts yet.</div>'
    else:
        cards = "".join(f"""
        <div class="chart-card">
          <img src="/img/visualizations/{f}" alt="{LABELS.get(f, f)}" loading="lazy"
               onclick="openImg('/img/visualizations/{f}','{LABELS.get(f, f)}')"
               style="cursor:pointer">
          <div class="chart-label">{LABELS.get(f, f.replace('_', ' ').replace('.png', '').title())}</div>
        </div>""" for f in charts)
        body = f"""<div class="section">
          <div class="section-title">📈 Charts & Plots — {len(charts)} images</div>
          <div class="chart-grid">{cards}</div>
        </div>"""
    return page("Visualizations", "Pipeline charts", body, "/visualizations")


@legacy_bp.route("/tracking")
def tracking():
    imgs = list_images(TRACKING_DIR)
    if not imgs:
        body = '<div class="empty"><div class="ico">🎯</div>No tracking frames yet.</div>'
    else:
        cards = "".join(f"""
        <div class="img-card"
             onclick="openImg('/img/visualizations/tracking_frames/{f}','{f}')">
          <img src="/img/visualizations/tracking_frames/{f}" loading="lazy" alt="{f}">
          <div class="img-info"><span class="img-badge badge-vlm">TRACK</span><br>{f}</div>
        </div>""" for f in imgs)
        body = f"""<div class="section">
          <div class="section-title">🎯 YOLO Tracking Frames — {len(imgs)} frames</div>
          <p style="color:#64748b;font-size:13px;margin-bottom:16px">
            Annotated by <code>model.track()</code> before VLM filtering.
          </p>
          <div class="img-grid" id="track-grid">{cards}</div>
          <div class="pagination" id="track-grid-pg"></div>
        </div>"""
    return page("Tracking Frames",
                f"{len(imgs)} YOLO annotated frames",
                body, "/tracking")


@legacy_bp.route("/live")
def live():
    live_js = r"""
const POLL_MS   = 2500;
const SHOW_MAX  = 80;

const ROUTE_COLORS = {
  "AUTO-ACCEPT"    : "#34d399",
  "VLM-YES"        : "#4ade80",
  "CACHED-ACCEPT"  : "#60a5fa",
  "LOW-CONF REJECT": "#94a3b8",
  "VLM-NO"         : "#f87171",
  "CACHED-REJECT"  : "#c084fc",
};

let seenFrames = new Set();

function routeStyle(route) {
  const col = ROUTE_COLORS[route] || "#e2e8f0";
  return `background:${col}22;color:${col};border:1px solid ${col}44;`;
}

function timeAgo(ts) {
  const s = Math.floor(Date.now()/1000 - ts);
  if (s <  60) return s + "s ago";
  if (s < 3600) return Math.floor(s/60) + "m ago";
  return Math.floor(s/3600) + "h ago";
}

function makeCard(item) {
  const col  = ROUTE_COLORS[item.route] || "#e2e8f0";
  const key  = item.frame_name + "_" + item.track_id + "_" + item.route;
  if (seenFrames.has(key)) return null;
  seenFrames.add(key);

  const card = document.createElement("div");
  card.className = "det-card";
  card.dataset.key = key;

  const imgSrc = `/api/frame/${encodeURIComponent(item.frame_name)}/${item.track_id}/${item.route}`;
  const reason = item.reason
    ? `<div class="det-reason">VLM: ${item.reason.substring(0,80)}${item.reason.length>80?"…":""}</div>`
    : "";

  card.innerHTML = `
    <img src="${imgSrc}" alt="${item.frame_name}" loading="lazy"
         onerror="this.style.display='none'"
         onclick="openImg('${imgSrc}','${item.label} ${item.confidence} | ${item.route} | Track#${item.track_id}')">
    <div class="det-body">
      <span class="det-route" style="${routeStyle(item.route)}">${item.route}</span>
      <div class="det-meta">
        <b style="color:${col}">${item.label}</b>
        &nbsp;conf <b>${item.confidence}</b>
        &nbsp;&bull;&nbsp; Track#<b>${item.track_id ?? "—"}</b><br>
        <span style="color:#475569">${item.frame_name} &bull; ${timeAgo(item.ts)}</span>
      </div>
      ${reason}
    </div>`;
  return card;
}

async function poll() {
  try {
    const resp = await fetch("/api/live?limit=60");
    const data = await resp.json();

    document.getElementById("cnt-total").textContent    = data.counters.total;
    document.getElementById("cnt-accepted").textContent = data.counters.accepted;
    document.getElementById("cnt-rejected").textContent = data.counters.rejected;
    document.getElementById("cnt-vlm").textContent      = data.counters.vlm_called;
    document.getElementById("cnt-cached").textContent   = data.counters.cached;
    document.getElementById("last-update").textContent  =
      "Last update: " + new Date().toLocaleTimeString();

    const grid = document.getElementById("det-grid");
    let inserted = 0;
    for (const item of data.items) {
      const card = makeCard(item);
      if (card) { grid.prepend(card); inserted++; }
    }

    while (grid.children.length > SHOW_MAX) {
      grid.removeChild(grid.lastChild);
    }
  } catch(e) {
    document.getElementById("live-status").textContent = "Connection error, retrying...";
  }
  setTimeout(poll, POLL_MS);
}

document.addEventListener("DOMContentLoaded", poll);
"""

    body = """
<div class="live-header">
  <div class="live-dot"></div>
  <div class="live-status" id="live-status">Receiving detections from Colab pipeline...</div>
  <span style="margin-left:auto;color:#475569;font-size:12px" id="last-update"></span>
</div>

<div class="cards" style="grid-template-columns:repeat(5,1fr)">
  <div class="card blue">
    <div class="label">Total Received</div>
    <div class="value" id="cnt-total">0</div>
  </div>
  <div class="card green">
    <div class="label">Accepted</div>
    <div class="value" id="cnt-accepted">0</div>
  </div>
  <div class="card red">
    <div class="label">Rejected</div>
    <div class="value" id="cnt-rejected">0</div>
  </div>
  <div class="card purple">
    <div class="label">VLM Calls</div>
    <div class="value" id="cnt-vlm">0</div>
  </div>
  <div class="card orange">
    <div class="label">Cached</div>
    <div class="value" id="cnt-cached">0</div>
  </div>
</div>

<div class="section">
  <div class="section-title">📡 Live Detection Stream  <span style="font-size:12px;color:#475569;font-weight:400">(auto-refreshes every 2.5 s)</span></div>
  <div class="det-grid" id="det-grid"></div>
  <div id="empty-msg" style="color:#475569;font-size:14px;text-align:center;padding:40px">
    Waiting for detections from Colab...
  </div>
</div>
"""
    return page("Live Feed", "Real-time detections streamed from the Colab pipeline",
                body, "/live", extra_js=live_js)
