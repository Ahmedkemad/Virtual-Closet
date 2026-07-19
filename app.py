import mimetypes
import os
import uuid

import replicate
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

import storage

load_dotenv()
mimetypes.add_type("application/manifest+json", ".webmanifest")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
CATEGORIES = ("top", "bottom", "shoes")
DEFAULT_DESCRIPTIONS = {"top": "a top", "bottom": "pants", "shoes": "shoes"}
REPLICATE_MODEL = os.environ.get(
    "REPLICATE_MODEL",
    "cuuupid/idm-vton:139cb1163486954531b765d4ac3bb6d3e02fe121151665adfc3b47e9ba3ebf67",
)

app = Flask(__name__)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def with_image_url(row: dict, folder: str) -> dict:
    return {**row, "image_url": storage.public_url(f"{folder}/{row['filename']}")}


def extract_url(output) -> str:
    # Some model versions return a single URL, others a list of URLs/FileOutput objects.
    return str(output[0] if isinstance(output, list) else output)


@app.route("/")
def index():
    if not storage.is_configured():
        return render_template("index.html", people=[], garments=[], history=[], storage_message=(
            "Photo saving isn't set up yet — add SUPABASE_URL and SUPABASE_SERVICE_KEY "
            "(see README) to start saving your library."
        ))

    try:
        people = [with_image_url(p, "people") for p in storage.db_select("people")]
        garments = [with_image_url(g, "garments") for g in storage.db_select("garments")]
        history = [with_image_url(h, "outputs") for h in storage.db_select("history")]
    except requests.RequestException:
        return render_template("index.html", people=[], garments=[], history=[], storage_message=(
            "Couldn't reach your saved photos right now — if you haven't used the app in a "
            "while, Supabase may be waking up. Try refreshing in about a minute."
        ))

    return render_template("index.html", people=people, garments=garments, history=history, storage_message=None)


def add_library_entry(table: str, folder: str, extra_fields: dict | None = None):
    if not storage.is_configured():
        return None, (jsonify({"error": "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY."}), 500)

    file = request.files.get("image")
    if not file or not allowed_file(file.filename):
        return None, (jsonify({"error": "Please upload a valid image (png/jpg/webp)."}), 400)

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    content_type = file.mimetype or f"image/{'jpeg' if ext == 'jpg' else ext}"

    try:
        storage.storage_upload(f"{folder}/{filename}", file.read(), content_type)
        label = request.form.get("label", "").strip()
        row = storage.db_insert(table, {"filename": filename, "label": label, **(extra_fields or {})})
    except requests.RequestException as exc:
        return None, (jsonify({"error": f"Could not save to Supabase: {exc}"}), 502)

    return with_image_url(row, folder), None


@app.route("/people", methods=["POST"])
def add_person():
    entry, error = add_library_entry("people", "people")
    if error:
        return error
    return jsonify(entry)


@app.route("/people/<item_id>", methods=["DELETE"])
def delete_person(item_id):
    try:
        row = storage.db_delete("people", item_id)
        if row:
            storage.storage_delete(f"people/{row['filename']}")
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not delete: {exc}"}), 502
    return "", 204


@app.route("/garments", methods=["POST"])
def add_garment():
    category = request.form.get("category", "")
    if category not in CATEGORIES:
        return jsonify({"error": "Category must be one of: top, bottom, shoes."}), 400
    entry, error = add_library_entry("garments", "garments", {"category": category})
    if error:
        return error
    return jsonify(entry)


@app.route("/garments/<item_id>", methods=["DELETE"])
def delete_garment(item_id):
    try:
        row = storage.db_delete("garments", item_id)
        if row:
            storage.storage_delete(f"garments/{row['filename']}")
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not delete: {exc}"}), 502
    return "", 204


@app.route("/try-on", methods=["POST"])
def try_on():
    if not os.environ.get("REPLICATE_API_TOKEN"):
        return jsonify({"error": "REPLICATE_API_TOKEN is not set. Copy .env.example to .env and add your token."}), 500
    if not storage.is_configured():
        return jsonify({"error": "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY."}), 500

    person_id = request.form.get("person_id")
    selected_ids = {cat: request.form.get(f"{cat}_id") for cat in CATEGORIES}
    selected_ids = {cat: gid for cat, gid in selected_ids.items() if gid}

    if not selected_ids:
        return jsonify({"error": "Please select at least one item to try on."}), 400

    try:
        people = {p["id"]: p for p in storage.db_select("people")}
        garments = {g["id"]: g for g in storage.db_select("garments")}
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not reach Supabase: {exc}"}), 502

    if person_id not in people:
        return jsonify({"error": "Please select or upload a photo of yourself."}), 400
    for cat, gid in selected_ids.items():
        if gid not in garments:
            return jsonify({"error": f"Please select a valid {cat}."}), 400

    current_image_url = storage.public_url(f"people/{people[person_id]['filename']}")
    used_descriptions = []

    # Chain each garment through the model in turn, using the previous result
    # as the next step's base photo — this single-garment model doesn't support
    # multiple garments in one call, so an outfit is composited one piece at a time.
    for cat in CATEGORIES:
        gid = selected_ids.get(cat)
        if not gid:
            continue

        garment = garments[gid]
        garment_url = storage.public_url(f"garments/{garment['filename']}")
        description = garment.get("label") or DEFAULT_DESCRIPTIONS[cat]
        used_descriptions.append(description)

        try:
            output = replicate.run(
                REPLICATE_MODEL,
                input={
                    "human_img": current_image_url,
                    "garm_img": garment_url,
                    "garment_des": description,
                },
            )
            current_image_url = extract_url(output)
        except Exception as exc:
            return jsonify({"error": f"Applying the {cat} failed: {exc}"}), 502

    garment_desc = " + ".join(used_descriptions)

    try:
        resp = requests.get(current_image_url, timeout=60)
        resp.raise_for_status()

        result_filename = f"{uuid.uuid4().hex}.png"
        storage.storage_upload(f"outputs/{result_filename}", resp.content, "image/png")
        row = storage.db_insert("history", {"filename": result_filename, "garment_desc": garment_desc})
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not save the result: {exc}"}), 502

    return jsonify(with_image_url(row, "outputs"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
