"""
app.py — Thin launcher for the VLM Dashboard.

HOW TO RUN
----------
1. Activate virtual environment:
       venv\\Scripts\\activate          (Windows)
       source venv/bin/activate        (Mac/Linux)

2. Install dependencies (first time only):
       pip install -r requirements.txt

3. Start the server:
       python app.py

4. Open http://localhost:5000 in your browser.
   If NGROK_AUTH_TOKEN is set in .env, the public URL is printed in the terminal.
"""

import os
from dotenv import load_dotenv
from flask import Flask

from database import init_db
from routes.ingest import ingest_bp
from routes.api import api_bp
from routes.legacy import legacy_bp

load_dotenv()

NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")

app = Flask(__name__)
app.register_blueprint(ingest_bp)
app.register_blueprint(api_bp)
app.register_blueprint(legacy_bp)


if __name__ == "__main__":
    init_db()

    public_url = None

    if NGROK_AUTH_TOKEN:
        try:
            from pyngrok import ngrok, conf as ngrok_conf
            ngrok_conf.get_default().auth_token = NGROK_AUTH_TOKEN
            tunnel     = ngrok.connect(5000, "http")
            public_url = tunnel.public_url
            print(f"\n  ngrok tunnel opened")
            print(f"  Public URL : {public_url}")
            print(f"\n  --> Paste this URL into NGROK_URL in your Colab notebook\n")
        except Exception as e:
            print(f"\n  ngrok failed: {e}")
            print("  Running locally only at http://localhost:5000\n")
    else:
        print("\n  NGROK_AUTH_TOKEN not set — running locally only")
        print("  Set it in .env to expose the dashboard publicly.\n")

    print(f"  Dashboard : http://localhost:5000")
    if public_url:
        print(f"  Public    : {public_url}")
    print()

    app.run(debug=False, port=5000, use_reloader=False)
