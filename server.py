"""
Portfolio Backend Server
Run: python server.py
Then open: http://localhost:5000
"""

import os
import json
import uuid
import mimetypes
from datetime import datetime
from flask import Flask, request, jsonify, send_file, send_from_directory, abort

app = Flask(__name__, static_folder='static')

# ── CONFIG ──────────────────────────────────────────────────────────────
OWNER_PASSWORD  = "Rusjade.123"   # ← CHANGE THIS before deploying!
UPLOAD_FOLDER   = "uploads"
DATA_FILE       = "portfolio_data.json"
MAX_FILE_MB     = 200               # max upload size in MB
ALLOWED_TYPES   = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"
}
# ────────────────────────────────────────────────────────────────────────

app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_MB * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── HELPERS ──────────────────────────────────────────────────────────────

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(items):
    with open(DATA_FILE, "w") as f:
        json.dump(items, f, indent=2)

def is_allowed(mime):
    return mime in ALLOWED_TYPES

# ── ROUTES ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# Auth
@app.route("/api/auth", methods=["POST"])
def auth():
    data = request.get_json(silent=True) or {}
    if data.get("password") == OWNER_PASSWORD:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Wrong password"}), 401

# Get all media items
@app.route("/api/items", methods=["GET"])
def get_items():
    return jsonify(load_data())

# Upload one or more files
@app.route("/api/upload", methods=["POST"])
def upload():
    # Simple password check via header
    if request.headers.get("X-Owner-Password") != OWNER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files"}), 400

    items = load_data()
    added = []

    for file in files:
        mime = file.content_type or mimetypes.guess_type(file.filename)[0] or ""
        if not is_allowed(mime):
            continue

        ext       = os.path.splitext(file.filename)[1].lower()
        uid       = str(uuid.uuid4())
        filename  = uid + ext
        filepath  = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        size_kb   = round(os.path.getsize(filepath) / 1024)
        kind      = "video" if mime.startswith("video") else "image"

        item = {
            "id":       uid,
            "filename": filename,
            "name":     os.path.splitext(file.filename)[0],
            "type":     kind,
            "mime":     mime,
            "size_kb":  size_kb,
            "url":      f"/uploads/{filename}",
            "date":     datetime.now().strftime("%B %d, %Y"),
            "created":  datetime.now().isoformat()
        }
        items.insert(0, item)
        added.append(item)

    save_data(items)
    return jsonify({"added": added, "total": len(items)})

# Delete a media item
@app.route("/api/items/<item_id>", methods=["DELETE"])
def delete_item(item_id):
    if request.headers.get("X-Owner-Password") != OWNER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    items = load_data()
    target = next((i for i in items if i["id"] == item_id), None)
    if not target:
        return jsonify({"error": "Not found"}), 404

    # Delete the file from disk
    filepath = os.path.join(UPLOAD_FOLDER, target["filename"])
    if os.path.exists(filepath):
        os.remove(filepath)

    items = [i for i in items if i["id"] != item_id]
    save_data(items)
    return jsonify({"ok": True, "remaining": len(items)})

# Update item name
@app.route("/api/items/<item_id>", methods=["PATCH"])
def update_item(item_id):
    if request.headers.get("X-Owner-Password") != OWNER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    data  = request.get_json(silent=True) or {}
    items = load_data()
    for item in items:
        if item["id"] == item_id:
            if "name" in data:
                item["name"] = data["name"][:120]
            save_data(items)
            return jsonify(item)
    return jsonify({"error": "Not found"}), 404

# Stats
@app.route("/api/stats", methods=["GET"])
def stats():
    items  = load_data()
    videos = [i for i in items if i["type"] == "video"]
    images = [i for i in items if i["type"] == "image"]
    total_kb = sum(i.get("size_kb", 0) for i in items)
    return jsonify({
        "total":  len(items),
        "videos": len(videos),
        "images": len(images),
        "size_mb": round(total_kb / 1024, 1)
    })

# ── MAIN ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🎬  Portfolio Server running at http://localhost:5000")
    print(f"📁  Uploads saved to: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"💾  Data file: {os.path.abspath(DATA_FILE)}\n")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
