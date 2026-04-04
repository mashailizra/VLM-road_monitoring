import base64
import json
import requests
from pathlib import Path

IMAGE_PATH = Path(r"images\Screenshot (81).png")
API_URL = "http://localhost:5000/yolo-inference"

# Read and encode image
with open(IMAGE_PATH, "rb") as f:
    b64_image = base64.b64encode(f.read()).decode("utf-8")

with open("image.log", "w") as log:
    log.write(b64_image)
print(f"Base64 written to image.log ({len(b64_image)} chars)")

payload = {
    "defect_type": "pothole",
    "confidence": 0.91,
    "model_name": "yolov8n",
    "image": b64_image,
}

# Print payload (truncate image for readability)
printable = {**payload, "image": b64_image[:40] + f"... ({len(b64_image)} chars)"}
print("Payload:")
print(json.dumps(printable, indent=2))
print()

# Send request
response = requests.post(API_URL, json=payload)
print(f"Status: {response.status_code}")
print("Response:", response.json())
