"""Entrypoint for sharekey."""
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB

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
                return send_file(file_path, download_name=item.content)
    return redirect("/404")

@app.route("/create", methods=["POST"])
def create_item():
    """Create a new item."""
    item_type_str = request.form.get("type", "").strip().lower()

    try:
        item_type = ItemType(item_type_str)
    except ValueError:
        item_type = None

    match item_type:
        case ItemType.URL | ItemType.TEXT:
            content = request.form.get("content", "")
            if not content:
                return "Content required", 400
            if item_type == ItemType.URL:
                parsed = urlparse(content)
                if parsed.scheme not in ["http", "https"]:
                    return "Invalid URL scheme", 400
            item = Item(datetime.now(tz="UTC"), item_type, content)

        case ItemType.FILE:
            if "file" not in request.files:
                return "No file provided", 400

            file = request.files["file"]
            safe_filename = secure_filename(file.filename)
            if not safe_filename:
                return "No/invalid filename", 400

            Path.mkdir("./uploads", exist_ok=True)
            item = Item(datetime.now(tz="UTC"), item_type, safe_filename)
            file_path = f"./uploads/{item.uuid}"
            file.save(file_path)

        case _:
            return "Bad Request", 400

    key = random.choice(word_list)  # noqa: S311
    word_list.remove(key)
    items[key] = item

    return key

def cleanup_old_items():
    """Remove items older than 5 minutes."""
    while True:
        time.sleep(60)
        current_time = datetime.now(tz="UTC")
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
