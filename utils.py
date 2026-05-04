import os
import base64
import uuid
from datetime import datetime

# Root directory for static assets
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

def save_image(b64_data, category, subcategory):
    """
    Decodes base64 image and saves to static/<category>/<subcategory>/<filename>.
    Returns the relative path from the static/ folder.
    """
    if not b64_data:
        return None

    # Strip data URI prefix if present
    if "base64," in b64_data:
        b64_data = b64_data.split("base64,", 1)[1]

    try:
        img_bytes = base64.b64decode(b64_data)
        
        # Ensure directories exist
        target_dir = os.path.join(STATIC_DIR, category, subcategory)
        os.makedirs(target_dir, exist_ok=True)

        # Generate unique filename: YYYYMMDD_HHMMSS_UUID.jpg
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        
        rel_path = os.path.join(category, subcategory, filename)
        abs_path = os.path.join(STATIC_DIR, rel_path)

        with open(abs_path, "wb") as f:
            f.write(img_bytes)

        return rel_path.replace("\\", "/") # Normalize for web/database
    except Exception as e:
        print(f"Error saving image: {e}")
        return None
