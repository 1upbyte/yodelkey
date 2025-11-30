import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum, auto
from uuid import UUID, uuid4
from typing import Optional
from flask import Flask, send_file, render_template, redirect, request, jsonify, make_response
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

with open("words.txt") as f:
    word_list = f.read().split(",")

class ItemType(StrEnum):
    URL = auto()
    TEXT = auto()
    FILE = auto()

@dataclass
class Item():
    creation_time: datetime
    type: ItemType
    content: str
    uuid: UUID = field(default_factory=uuid4)

items: dict[str, Item] = {"test": Item(creation_time=datetime.now(), type=ItemType.TEXT, content="<script>alert('hello')</script>")} 

@app.get("/")
def root():
    return render_template("index.html")

@app.get("/404")
def not_found():
    return "not found", 404

@app.get("/<key>")
def handle_key(key: str):
    item = items.get(key)
    if item:
        print(item.type)
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
    item_type_str = request.form.get("type", "").strip().lower()
    
    try:
        item_type = ItemType(item_type_str)
    except ValueError:
        item_type = None
    
    match item_type:
        case ItemType.URL | ItemType.TEXT:
            item = Item(creation_time=datetime.now(), type=item_type, content=request.form.get("content"))
        case ItemType.FILE:
            if 'file' not in request.files:
                return "No file provided", 400
            
            file = request.files['file']
            if file.filename == '':
                return "No file selected", 400
            
            os.makedirs("./uploads", exist_ok=True)
            
            item = Item(creation_time=datetime.now(), type=item_type, content=file.filename)
            file_path = f"./uploads/{item.uuid}"
            file.save(file_path)
        case _:
            return "Bad Request", 400

    random_index = random.randint(0, len(word_list) - 1)
    key = word_list[random_index]
    word_list.remove(key)

    items[key] = item

    print(items[key])

    return key

if __name__ == "__main__":
    app.run(debug=True)