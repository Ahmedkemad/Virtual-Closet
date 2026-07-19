import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import replicate
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
OUTPUT_DIR = BASE_DIR / "static" / "outputs"
HISTORY_FILE = BASE_DIR / "closet_history.json"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
REPLICATE_MODEL = os.environ.get(
    "REPLICATE_MODEL",
    "cuuupid/idm-vton:139cb1163486954531b765d4ac3bb6d3e02fe121151665adfc3b47e9ba3ebf67",
)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def load_history() -> list:
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)


def save_history(history: list) -> None:
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def save_upload(file_storage, prefix: str) -> Path:
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"{prefix}_{uuid.uuid4().hex}.{ext}")
    path = UPLOAD_DIR / filename
    file_storage.save(path)
    return path


@app.route("/")
def index():
    history = list(reversed(load_history()))
    return render_template("index.html", history=history)


@app.route("/try-on", methods=["POST"])
def try_on():
    if not os.environ.get("REPLICATE_API_TOKEN"):
        return jsonify({"error": "REPLICATE_API_TOKEN is not set. Copy .env.example to .env and add your token."}), 500

    person_file = request.files.get("person_image")
    garment_file = request.files.get("garment_image")
    garment_desc = request.form.get("garment_desc", "a garment")

    if not person_file or not allowed_file(person_file.filename):
        return jsonify({"error": "Please upload a valid photo of yourself (png/jpg/webp)."}), 400
    if not garment_file or not allowed_file(garment_file.filename):
        return jsonify({"error": "Please upload a valid photo of the garment (png/jpg/webp)."}), 400

    person_path = save_upload(person_file, "person")
    garment_path = save_upload(garment_file, "garment")

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

    history = load_history()
    entry = {
        "id": uuid.uuid4().hex,
        "person_image": f"uploads/{person_path.name}",
        "garment_image": f"uploads/{garment_path.name}",
        "garment_desc": garment_desc,
        "result_image": f"outputs/{result_filename}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    history.append(entry)
    save_history(history)

    return jsonify(entry)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
