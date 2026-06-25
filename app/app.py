"""Entrypoint for sharekey."""
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum, auto
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from flask import (
    Flask,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
)
from werkzeug.serving import run_simple
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB


@app.after_request
def add_cors_headers(response):
    """Allow browser extensions (and any origin) to call this API."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/create", methods=["OPTIONS"])
def create_preflight():
    """Handle CORS preflight for /create."""
    return "", 204

with Path.open("words.txt") as f:
    word_list = f.read().split(",")

class ItemType(StrEnum):
    """Enum for different types of items."""

    URL = auto()
    TEXT = auto()
    FILE = auto()

@dataclass
class Item:
    """Item for different types of content."""

    creation_time: datetime
    type: ItemType
    content: str
    uuid: UUID = field(default_factory=uuid4)

items: dict[str, Item] = {}

@app.get("/")
def root():
    """Return index page."""
    return render_template("index.html")

@app.get("/favicon.ico")
def favicon():
    """Give the favicon."""
    return send_file("./static/favicon.ico")

@app.get("/404")
def not_found():
    """Return 404."""
    return "not found", 404

@app.get("/<key>")
def handle_key(key: str):
    """Handle key (redirect, text, or file)."""
    item = items.get(key)
    if item:
        match item.type:
            case ItemType.URL:
                return redirect(item.content)
            case ItemType.TEXT:
                response = make_response(item.content)
                response.headers["Content-Type"] = "text/plain"
                return response
            case ItemType.FILE:
                file_path = f"./uploads/{item.uuid}"
                return send_file(file_path, download_name=item.content,
                                 as_attachment=True)
    return redirect("/404")

@app.route("/create", methods=["GET", "POST", "PUT"])
@app.route("/", methods=["POST"])
@app.route("/<filename>", methods=["PUT"])
def create_item(filename: str = ""):
    """Create a new item with inferred type."""
    # 1. Check for file upload first
    if request.method == "PUT" and filename:
        content = secure_filename(filename)
        if not content:
            return "Content required", 400
        item_type = ItemType.FILE

    elif request.method == "POST" and "file" in request.files:
        file = request.files["file"]
        content = secure_filename(file.filename)
        if not content:
            return "No/invalid filename", 400
        item_type = ItemType.FILE

    # 2. Otherwise, treat as Text or URL
    else:
        content = request.args.get("content")

        if not content:
            return "Content required", 400

        # Infer if it's a URL or Text
        if content.startswith(("http://", "https://")):
            item_type = ItemType.URL
            parsed = urlparse(content)
            content = parsed.geturl()
        else:
            item_type = ItemType.TEXT

    # 3. Create item and save file if needed
    item = Item(datetime.now(tz=UTC), item_type, content)

    if item_type == ItemType.FILE:
        Path("./uploads").mkdir(exist_ok=True)
        if request.method == "PUT":
            with open(f"./uploads/{item.uuid}", "wb") as f:
                f.write(request.data)
        else:
            file.save(f"./uploads/{item.uuid}")

    # 4. Generate key
    key = secrets.choice(word_list)
    word_list.remove(key)
    items[key] = item

    return f"{key}\n"

def cleanup_old_items():
    """Remove items older than 5 minutes."""
    while True:
        time.sleep(60)
        current_time = datetime.now(tz=UTC)
        keys_to_delete = []

        for key, item in items.items():
            age = current_time - item.creation_time
            if age >= timedelta(minutes=5):
                keys_to_delete.append(key)

                if item.type == ItemType.FILE:
                    file_path = f"./uploads/{item.uuid}"
                    Path.unlink(file_path, missing_ok=True)

        for key in keys_to_delete:
            del items[key]
            word_list.append(key)

if __name__ == "__main__":
    cleanup_thread = threading.Thread(target=cleanup_old_items, daemon=True)
    cleanup_thread.start()
    run_simple("0.0.0.0", 5000, app)  # noqa: S104

