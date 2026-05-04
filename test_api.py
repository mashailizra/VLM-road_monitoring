import base64
import json
import requests
import os
from pathlib import Path

# --- Configuration ---
API_BASE_URL = "http://localhost:5000"
# Use an existing image from the repository for testing
IMAGE_PATH = Path(r"images/Screenshot (81).png")

def test_yolo_inference(image_b64):
    print("\n--- Testing YOLO Inference ---")
    payload = {
        "defect_type": "pothole",
        "confidence": 0.89,
        "model_name": "yolov8-test",
        "image": image_b64,
        "status": "accepted"
    }
    
    url = f"{API_BASE_URL}/yolo-inference"
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_vlm_confirmation(image_b64):
    print("\n--- Testing VLM Confirmation (Yes) ---")
    payload = {
        "defect_type": "pothole",
        "model": "gemini-1.5-flash",
        "reasoning": "Clear structural failure in the asphalt with depth exceeding 5cm.",
        "image": image_b64
    }
    
    url = f"{API_BASE_URL}/vlm-yes"
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_vlm_rejection(image_b64):
    print("\n--- Testing VLM Rejection (No) ---")
    payload = {
        "defect_type": "crack",
        "model": "gemini-1.5-flash",
        "reasoning": "This appears to be a shadow, not a road defect.",
        "image": image_b64
    }
    
    url = f"{API_BASE_URL}/vlm-no"
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.text}")

def test_legacy_ingest(image_b64):
    print("\n--- Testing Legacy Ingest (Live Feed) Persistence ---")
    payload = {
        "route": "VLM-YES",
        "label": "pothole",
        "confidence": 0.95,
        "track_id": 101,
        "frame_name": "test_frame_001",
        "reasoning": "Confidence is high due to circular shape and typical shadow pattern.",
        "frame_b64": image_b64
    }
    
    url = f"{API_BASE_URL}/ingest"
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    if not IMAGE_PATH.exists():
        print(f"Error: Test image not found at {IMAGE_PATH}")
        # Create a dummy base64 if image is missing for demonstration
        b64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    else:
        with open(IMAGE_PATH, "rb") as f:
            b64_image = base64.b64encode(f.read()).decode("utf-8")

    # Run tests
    try:
        test_yolo_inference(b64_image)
        test_vlm_confirmation(b64_image)
        test_vlm_rejection(b64_image)
        test_legacy_ingest(b64_image)
        
        print("\nAll tests sent successfully! Check your dashboard and database history.")
    except Exception as e:
        print(f"\nError connecting to server: {e}")
        print("Make sure 'python app.py' is running.")
