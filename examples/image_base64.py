import base64
import time
import sys
from pathlib import Path

def image_to_base64(image_path):
    start = time.perf_counter()
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    elapsed = time.perf_counter() - start
    print(f"Encode time: {elapsed*1000:.3f} ms  |  base64 length: {len(b64)} chars")
    return b64

def base64_to_image(b64_string, output_path):
    start = time.perf_counter()
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(b64_string))
    elapsed = time.perf_counter() - start
    print(f"Decode time: {elapsed*1000:.3f} ms  |  saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python image_base64.py <image_file>")
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(1)

    out = src.with_stem(src.stem + "_decoded")

    print(f"\nSource: {src}")
    b64 = image_to_base64(src)
    base64_to_image(b64, out)
    print("Done.")
