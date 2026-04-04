import base64

image_path = "Screenshot (81).png"

with open(image_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

print(b64)
