import json
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import replicate
import requests
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, render_template, request
from werkzeug.utils import secure_filename

load_dotenv()
mimetypes.add_type("application/manifest+json", ".webmanifest")

BASE_DIR = Path(__file__).resolve().parent
PEOPLE_DIR = BASE_DIR / "static" / "people"
GARMENTS_DIR = BASE_DIR / "static" / "garments"
OUTPUT_DIR = BASE_DIR / "static" / "outputs"
PEOPLE_FILE = BASE_DIR / "people.json"
GARMENTS_FILE = BASE_DIR / "garments.json"
HISTORY_FILE = BASE_DIR / "closet_history.json"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
REPLICATE_MODEL = os.environ.get(
    "REPLICATE_MODEL",
    "cuuupid/idm-vton:139cb1163486954531b765d4ac3bb6d3e02fe121151665adfc3b47e9ba3ebf67",
)

PEOPLE_DIR.mkdir(parents=True, exist_ok=True)
GARMENTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def load_json(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, "r") as f:
        return json.load(f)


def save_json(path: Path, data: list) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def save_library_image(file_storage, directory: Path, label: str) -> dict:
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    file_storage.save(directory / filename)
    return {
        "id": uuid.uuid4().hex,
        "filename": filename,
        "label": label,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def add_library_entry(directory: Path, store_file: Path, field_name: str):
    file = request.files.get(field_name)
    if not file or not allowed_file(file.filename):
        return None, (jsonify({"error": "Please upload a valid image (png/jpg/webp)."}), 400)

    label = request.form.get("label", "").strip()
    entry = save_library_image(file, directory, label)
    items = load_json(store_file)
    items.append(entry)
    save_json(store_file, items)
    return entry, None


def delete_library_entry(directory: Path, store_file: Path, item_id: str):
    items = load_json(store_file)
    remaining = [i for i in items if i["id"] != item_id]
    if len(remaining) == len(items):
        abort(404)
    removed = next(i for i in items if i["id"] == item_id)
    save_json(store_file, remaining)
    (directory / removed["filename"]).unlink(missing_ok=True)


@app.route("/")
def index():
    people = list(reversed(load_json(PEOPLE_FILE)))
    garments = list(reversed(load_json(GARMENTS_FILE)))
    history = list(reversed(load_json(HISTORY_FILE)))
    return render_template("index.html", people=people, garments=garments, history=history)


@app.route("/people", methods=["POST"])
def add_person():
    entry, error = add_library_entry(PEOPLE_DIR, PEOPLE_FILE, "image")
    if error:
        return error
    return jsonify(entry)


@app.route("/people/<item_id>", methods=["DELETE"])
def delete_person(item_id):
    delete_library_entry(PEOPLE_DIR, PEOPLE_FILE, item_id)
    return "", 204


@app.route("/garments", methods=["POST"])
def add_garment():
    entry, error = add_library_entry(GARMENTS_DIR, GARMENTS_FILE, "image")
    if error:
        return error
    return jsonify(entry)


@app.route("/garments/<item_id>", methods=["DELETE"])
def delete_garment(item_id):
    delete_library_entry(GARMENTS_DIR, GARMENTS_FILE, item_id)
    return "", 204


@app.route("/try-on", methods=["POST"])
def try_on():
    if not os.environ.get("REPLICATE_API_TOKEN"):
        return jsonify({"error": "REPLICATE_API_TOKEN is not set. Copy .env.example to .env and add your token."}), 500

    person_id = request.form.get("person_id")
    garment_id = request.form.get("garment_id")
    garment_desc = request.form.get("garment_desc", "a garment")

    people = {p["id"]: p for p in load_json(PEOPLE_FILE)}
    garments = {g["id"]: g for g in load_json(GARMENTS_FILE)}

    if person_id not in people:
        return jsonify({"error": "Please select or upload a photo of yourself."}), 400
    if garment_id not in garments:
        return jsonify({"error": "Please select or upload a garment photo."}), 400

    person_path = PEOPLE_DIR / people[person_id]["filename"]
    garment_path = GARMENTS_DIR / garments[garment_id]["filename"]

    try:
        with open(person_path, "rb") as human_img, open(garment_path, "rb") as garm_img:
            output = replicate.run(
                REPLICATE_MODEL,
                input={
                    "human_img": human_img,
                    "garm_img": garm_img,
                    "garment_des": garment_desc,
                },
            )
    except Exception as exc:
        return jsonify({"error": f"Try-on model call failed: {exc}"}), 502

    # Some model versions return a single URL, others a list of URLs/FileOutput objects.
    result_url = output[0] if isinstance(output, list) else output
    result_url = str(result_url)

    result_filename = f"result_{uuid.uuid4().hex}.png"
    result_path = OUTPUT_DIR / result_filename
    resp = requests.get(result_url, timeout=60)
    resp.raise_for_status()
    with open(result_path, "wb") as f:
        f.write(resp.content)

    history = load_json(HISTORY_FILE)
    entry = {
        "id": uuid.uuid4().hex,
        "garment_desc": garment_desc,
        "result_image": f"outputs/{result_filename}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    history.append(entry)
    save_json(HISTORY_FILE, history)

    return jsonify(entry)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
