# VLM Dashboard — Project Guide

## What This Project Does

A real-time web dashboard that receives road defect detections from a YOLO model and VLM (Vision-Language Model) rejection results, stores them in a database, and displays them in a browser.

**Pipeline flow:**
```
Colab Notebook
  → YOLO detects road defect
      → POST /yolo-inference   (stored in detections table)
  → VLM rejects the detection
      → POST /vlm-no           (stored in vlm_no_results table)
  → Dashboard shows both at http://localhost:5000
```

---

## How to Run

```bash
# 1. Activate the virtual environment
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 2. Install dependencies (first time only)
pip install -r requirements.txt

# 3. Start the server
python app.py
```

Open your browser at **http://localhost:5000**

If `NGROK_AUTH_TOKEN` is set in `.env`, a public URL will be printed in the terminal. Paste that URL into your Colab notebook.

---

## Folder Structure

```
VLM-DASHBOARD/
├── app.py              Main server (thin launcher, ~50 lines)
├── database.py         SQLite helpers — all DB logic here
├── CLAUDE.md           This file
├── requirements.txt    Python dependencies
├── .env                Secrets (ngrok token, paths) — never commit this
│
├── routes/
│   ├── ingest.py       POST /yolo-inference and POST /vlm-no
│   ├── api.py          GET /api/detections, /api/vlm-no, /api/stats, /api/image
│   └── legacy.py       All original routes preserved (/live, /accepted, etc.)
│
├── templates/
│   └── dashboard.html  The main dashboard page (Bootstrap 5)
│
├── static/
│   ├── dashboard.js    Frontend JavaScript (polling, filters, table)
│   └── images/
│       ├── yolo/       YOLO detection images uploaded via /yolo-inference
│       └── vlm/        VLM rejection images uploaded via /vlm-no
│
├── examples/
│   ├── yolo_payload.json   Example JSON for POST /yolo-inference
│   ├── vlm_payload.json    Example JSON for POST /vlm-no
│   ├── send_yolo.py        Python script to test /yolo-inference
│   └── send_vlm.py         Python script to test /vlm-no
│
└── output/             Original pipeline output folder (untouched)
```

---

## Database Schema

File: `detections.db` (created automatically on first run)

### `detections` table — YOLO results
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Auto-increment primary key |
| defect_type | TEXT | e.g. "pothole", "crack" |
| confidence | REAL | 0.0 – 1.0 |
| timestamp | TEXT | **Auto-filled by server** (do not send) |
| model_name | TEXT | e.g. "yolov8n" |
| image | image_field

### `vlm_no_results` table — VLM rejections
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Auto-increment primary key |
| defect_type | TEXT | e.g. "pothole", "crack" |
| image | image_field
| timestamp | TEXT | **Auto-filled by server** (do not send) |
| model | TEXT | e.g. "gemini-1.5-flash" |
| reasoning| TEXT

---

## API Endpoints

### Send data (from Colab pipeline)

#### `POST /yolo-inference`
```json
{
  "defect_type": "pothole",
  "confidence": 0.87,
  "model_name": "yolov8n",
  "image": "<base64-encoded JPEG>"
}
```
Response: `{"status": "ok", "detection_id": 1}`

> `timestamp` is **not** required — the server sets it automatically.

#### `POST /vlm-no`
```json
{
  "detection_id": 1,
  "model": "gemini-1.5-flash",
  "image": "<base64-encoded JPEG>"
  "reasoning":"this was etc.."
}
```
Response: `{"status": "ok", "vlm_no_id": 1}`

> `detection_id` is optional — include it only if you want to link back to a specific YOLO detection.

---

### Read data (used by the dashboard frontend)

| Method | Endpoint | Query params |
|--------|----------|-------------|
| GET | `/api/detections` | `defect_type`, `start`, `end`, `limit` |
| GET | `/api/vlm-no` | `model`, `start`, `end`, `limit` |
| GET | `/api/stats` | — |
| GET | `/api/image/<path>` | — |

---

### Legacy endpoints (original pipeline compatibility)

These still work exactly as before:

| Endpoint | Purpose |
|----------|---------|
| `POST /ingest` | Original single endpoint (still accepted) |
| `GET /live` | Live feed page |
| `GET /accepted` | Accepted detections page |
| `GET /rejected` | Rejected detections page |
| `GET /reasoning` | VLM reasoning page |
| `GET /visualizations` | Charts page |
| `GET /tracking` | Tracking frames page |

---

## How to Connect from Colab

```python
import requests
import base64

DASHBOARD_URL = "https://your-ngrok-url.ngrok-free.app"  # from terminal output

# Step 1: Send YOLO detection
def send_yolo(defect_type, confidence, model_name, image_path=None):
    payload = {
        "defect_type": defect_type,
        "confidence": confidence,
        "model_name": model_name,
    }
    if image_path:
        with open(image_path, "rb") as f:
            payload["image"] = base64.b64encode(f.read()).decode("utf-8")
    r = requests.post(f"{DASHBOARD_URL}/yolo-inference", json=payload)
    return r.json()["detection_id"]  # save this for the VLM step

# Step 2: If VLM says NO, send rejection
def send_vlm_no(detection_id, model_name, image_path=None):
    payload = {
        "detection_id": detection_id,
        "model": model_name,
    }
    if image_path:
        with open(image_path, "rb") as f:
            payload["image"] = base64.b64encode(f.read()).decode("utf-8")
    requests.post(f"{DASHBOARD_URL}/vlm-no", json=payload)
```

---

## Environment Variables (`.env` file)

```
NGROK_AUTH_TOKEN=your_token_here
OUTPUT_ROOT=C:\Users\...\output
DB_PATH=detections.db
```

---

## Running the Example Scripts

```bash
# Test YOLO endpoint
python examples/send_yolo.py

# Test VLM-no endpoint
python examples/send_vlm.py
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: flask` | Run `pip install -r requirements.txt` |
| ngrok URL not working | Check `NGROK_AUTH_TOKEN` in `.env` |
| Images not showing | Check `static/images/yolo/` and `static/images/vlm/` exist |
| Database not found | Run `python app.py` once — it creates `detections.db` automatically |
