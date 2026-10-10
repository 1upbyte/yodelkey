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
from werkzeug.security import check_password_hash, generate_password_hash
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

WORDLIST_DIR = Path(__file__).resolve().parent / "wordlists"
BASE_WORDLIST = "base.txt"
DEFAULT_WALLPAPER = "wallpaper.jpg"

SEASONAL_THEMES = {
    # (month, day); the end is exclusive.
    ((10, 1), (12, 1)): {
        "file": "autumn.txt",
        "wallpaper": "autumn.webp",
        "author": "AnasAbdin",
        "link": "https://steamcommunity.com/sharedfiles/filedetails/?id=3328819032",
    },
}

def current_theme() -> dict[str, str] | None:
    """Find the theme active at the current local time."""
    now = datetime.now()
    timestamp = (now.month, now.day)
    for (start, end), theme in SEASONAL_THEMES.items():
        active = (start <= timestamp < end if start < end
                  else timestamp >= start or timestamp < end)
        if active:
            return theme
    return None

def load_words(filename: str) -> list[str]:
    """Load unique words from a comma-separated wordlist."""
    return list(dict.fromkeys(
        word.strip() for word in (WORDLIST_DIR / filename).read_text().split(",")
        if word.strip()
    ))

seasonal_files = {theme["file"] for theme in SEASONAL_THEMES.values()}
word_pools = {filename: load_words(filename) for filename in seasonal_files}
seasonal_words = set().union(*(set(words) for words in word_pools.values()))
word_pools[BASE_WORDLIST] = [
    word for word in load_words(BASE_WORDLIST) if word not in seasonal_words
]
word_owner = {
    word: filename for filename, words in word_pools.items() for word in words
}
word_lock = threading.Lock()

@app.context_processor
def seasonal_theme():
    """Provide the current wallpaper to every rendered page."""
    theme = current_theme()
    return {
        "wallpaper": theme["wallpaper"] if theme else DEFAULT_WALLPAPER,
        "wallpaper_link": theme["link"] if theme else "",
        "wallpaper_author": theme["author"] if theme else "",
    }

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
    password_hash: str | None = None
    burn_after_read: bool = False

items: dict[str, Item] = {}

def is_browser_request() -> bool:
    """Guess whether the request came from a browser rather than a CLI tool."""
    return "Mozilla" in request.headers.get("User-Agent", "")

def get_supplied_password() -> str | None:
    """Read the password from the query string, trying a few aliases."""
    for param in ("pass", "code", "password"):
        value = request.args.get(param)
        if value:
            return value
    return None

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
    if not item:
        return redirect("/404")

    if item.password_hash:
        supplied = get_supplied_password()
        if not supplied or not check_password_hash(item.password_hash, supplied):
            if not is_browser_request():
                return "Password incorrect", 403
            wrong = supplied is not None
            return render_template("password.html", wrong=wrong), 403

    if item.burn_after_read:
        with word_lock:
            # Another request may have consumed the key while password was checked.
            if items.get(key) is not item:
                return redirect("/404")
            response = item_response(item)
            del items[key]
            word_pools[word_owner[key]].append(key)
            if item.type == ItemType.FILE:
                # Keep the open file available until the download finishes.
                response.direct_passthrough = False

                @response.call_on_close
                def close_upload() -> None:
                    Path(f"./uploads/{item.uuid}").unlink(missing_ok=True)
            return response

    return item_response(item)

def item_response(item: Item):
    """Return the stored URL, text, or file."""
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

@app.route("/create", methods=["GET", "POST", "PUT"])
@app.route("/", methods=["POST", "PUT"])
@app.route("/<filename>", methods=["PUT"])
def create_item(filename: str = "no_filename"):
    """Create a new item with inferred type."""
    # 1. Check for file upload first
    if request.method == "PUT":
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
    password = get_supplied_password()
    password_hash = generate_password_hash(password) if password else None
    item = Item(datetime.now(tz=UTC), item_type, content,
                password_hash=password_hash,
                burn_after_read=request.args.get("burn", "").lower() in {"1", "true"})

    if item_type == ItemType.FILE:
        Path("./uploads").mkdir(exist_ok=True)
        if request.method == "PUT":
            with open(f"./uploads/{item.uuid}", "wb") as f:
                f.write(request.data)
        else:
            file.save(f"./uploads/{item.uuid}")

    # 4. Use the seasonal wordlist first, then the base wordlist.
    with word_lock:
        theme = current_theme()
        seasonal_pool = word_pools[theme["file"]] if theme else []
        pool = seasonal_pool or word_pools[BASE_WORDLIST]
        if not pool:
            if item_type == ItemType.FILE:
                Path(f"./uploads/{item.uuid}").unlink(missing_ok=True)
            return "No keys available", 503
        key = secrets.choice(pool)
        pool.remove(key)
        items[key] = item

    return f"{key}\n"

def cleanup_old_items():
    """Remove items older than 5 minutes."""
    while True:
        time.sleep(60)
        current_time = datetime.now(tz=UTC)
        keys_to_delete = []

        with word_lock:
            for key, item in items.items():
                age = current_time - item.creation_time
                if age >= timedelta(minutes=5):
                    keys_to_delete.append(key)

                    if item.type == ItemType.FILE:
                        file_path = f"./uploads/{item.uuid}"
                        Path(file_path).unlink(missing_ok=True)

            for key in keys_to_delete:
                del items[key]
                word_pools[word_owner[key]].append(key)

if __name__ == "__main__":
    cleanup_thread = threading.Thread(target=cleanup_old_items, daemon=True)
    cleanup_thread.start()
    run_simple("0.0.0.0", 5000, app)  # noqa: S104

