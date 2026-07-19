import functools
import mimetypes
import os
import uuid
from datetime import timedelta

import replicate
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

import auth
import storage

load_dotenv()
mimetypes.add_type("application/manifest+json", ".webmanifest")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
CATEGORIES = ("top", "bottom")
DEFAULT_DESCRIPTIONS = {"top": "a top", "bottom": "pants"}
# IDM-VTON needs to be told which body region a garment belongs on, or it
# defaults to treating everything as upper-body clothing.
MODEL_CATEGORIES = {"top": "upper_body", "bottom": "lower_body"}
REPLICATE_MODEL = os.environ.get(
    "REPLICATE_MODEL",
    "cuuupid/idm-vton:139cb1163486954531b765d4ac3bb6d3e02fe121151665adfc3b47e9ba3ebf67",
)
INVITE_CODE = os.environ.get("INVITE_CODE", "")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "")
app.permanent_session_lifetime = timedelta(days=365)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def with_image_url(row: dict, folder: str) -> dict:
    return {**row, "image_url": storage.public_url(f"{folder}/{row['user_id']}/{row['filename']}")}


def extract_url(output) -> str:
    # Some model versions return a single URL, others a list of URLs/FileOutput objects.
    return str(output[0] if isinstance(output, list) else output)


def current_user_id():
    return session.get("user_id")


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user_id():
            if request.path == "/" or request.method == "GET":
                return redirect(url_for("login"))
            return jsonify({"error": "Please log in again."}), 401
        return view(*args, **kwargs)
    return wrapped


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user_id():
        return redirect(url_for("index"))
    if request.method == "GET":
        return render_template("auth.html", mode="signup")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    invite_code = request.form.get("invite_code", "")

    if not INVITE_CODE:
        return render_template("auth.html", mode="signup", error="Signups aren't configured. Set INVITE_CODE.")
    if invite_code != INVITE_CODE:
        return render_template("auth.html", mode="signup", error="That invite code isn't right.")
    if not auth.is_configured():
        return render_template("auth.html", mode="signup", error="Login isn't configured. Set SUPABASE_ANON_KEY.")

    try:
        user_id = auth.signup(email, password)
    except ValueError as exc:
        return render_template("auth.html", mode="signup", error=str(exc))

    session.permanent = True
    session["user_id"] = user_id
    session["email"] = email
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user_id():
        return redirect(url_for("index"))
    if request.method == "GET":
        return render_template("auth.html", mode="login")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not auth.is_configured():
        return render_template("auth.html", mode="login", error="Login isn't configured. Set SUPABASE_ANON_KEY.")

    try:
        user_id = auth.login(email, password)
    except ValueError as exc:
        return render_template("auth.html", mode="login", error=str(exc))

    session.permanent = True
    session["user_id"] = user_id
    session["email"] = email
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    uid = current_user_id()

    if not storage.is_configured():
        return render_template("index.html", people=[], garments=[], history=[], user_email=session.get("email"), storage_message=(
            "Photo saving isn't set up yet — add SUPABASE_URL and SUPABASE_SERVICE_KEY "
            "(see README) to start saving your library."
        ))

    try:
        people = [with_image_url(p, "people") for p in storage.db_select("people", {"user_id": uid})]
        garments = [with_image_url(g, "garments") for g in storage.db_select("garments", {"user_id": uid})]
        history = [with_image_url(h, "outputs") for h in storage.db_select("history", {"user_id": uid})]
    except requests.RequestException:
        return render_template("index.html", people=[], garments=[], history=[], user_email=session.get("email"), storage_message=(
            "Couldn't reach your saved photos right now — if you haven't used the app in a "
            "while, Supabase may be waking up. Try refreshing in about a minute."
        ))

    return render_template("index.html", people=people, garments=garments, history=history, user_email=session.get("email"), storage_message=None)


def add_library_entry(table: str, folder: str, uid: str, extra_fields: dict | None = None):
    if not storage.is_configured():
        return None, (jsonify({"error": "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY."}), 500)

    file = request.files.get("image")
    if not file or not allowed_file(file.filename):
        return None, (jsonify({"error": "Please upload a valid image (png/jpg/webp)."}), 400)

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    content_type = file.mimetype or f"image/{'jpeg' if ext == 'jpg' else ext}"

    try:
        storage.storage_upload(f"{folder}/{uid}/{filename}", file.read(), content_type)
        label = request.form.get("label", "").strip()
        row = storage.db_insert(table, {"filename": filename, "label": label, "user_id": uid, **(extra_fields or {})})
    except requests.RequestException as exc:
        return None, (jsonify({"error": f"Could not save to Supabase: {exc}"}), 502)

    return with_image_url(row, folder), None


@app.route("/people", methods=["POST"])
@login_required
def add_person():
    entry, error = add_library_entry("people", "people", current_user_id())
    if error:
        return error
    return jsonify(entry)


@app.route("/people/<item_id>", methods=["DELETE"])
@login_required
def delete_person(item_id):
    uid = current_user_id()
    try:
        row = storage.db_delete("people", item_id, {"user_id": uid})
        if row:
            storage.storage_delete(f"people/{uid}/{row['filename']}")
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not delete: {exc}"}), 502
    return "", 204


@app.route("/garments", methods=["POST"])
@login_required
def add_garment():
    category = request.form.get("category", "")
    if category not in CATEGORIES:
        return jsonify({"error": "Category must be one of: top, bottom."}), 400
    entry, error = add_library_entry("garments", "garments", current_user_id(), {"category": category})
    if error:
        return error
    return jsonify(entry)


@app.route("/garments/<item_id>", methods=["DELETE"])
@login_required
def delete_garment(item_id):
    uid = current_user_id()
    try:
        row = storage.db_delete("garments", item_id, {"user_id": uid})
        if row:
            storage.storage_delete(f"garments/{uid}/{row['filename']}")
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not delete: {exc}"}), 502
    return "", 204


@app.route("/history/<item_id>", methods=["DELETE"])
@login_required
def delete_history(item_id):
    uid = current_user_id()
    try:
        row = storage.db_delete("history", item_id, {"user_id": uid})
        if row:
            storage.storage_delete(f"outputs/{uid}/{row['filename']}")
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not delete: {exc}"}), 502
    return "", 204


@app.route("/try-on", methods=["POST"])
@login_required
def try_on():
    uid = current_user_id()

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
        people = {p["id"]: p for p in storage.db_select("people", {"user_id": uid})}
        garments = {g["id"]: g for g in storage.db_select("garments", {"user_id": uid})}
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not reach Supabase: {exc}"}), 502

    if person_id not in people:
        return jsonify({"error": "Please select or upload a photo of yourself."}), 400
    for cat, gid in selected_ids.items():
        if gid not in garments:
            return jsonify({"error": f"Please select a valid {cat}."}), 400

    current_image_url = storage.public_url(f"people/{uid}/{people[person_id]['filename']}")
    used_descriptions = []

    # Chain each garment through the model in turn, using the previous result
    # as the next step's base photo — this single-garment model doesn't support
    # multiple garments in one call, so an outfit is composited one piece at a time.
    for cat in CATEGORIES:
        gid = selected_ids.get(cat)
        if not gid:
            continue

        garment = garments[gid]
        garment_url = storage.public_url(f"garments/{uid}/{garment['filename']}")
        description = garment.get("label") or DEFAULT_DESCRIPTIONS[cat]
        used_descriptions.append(description)

        try:
            output = replicate.run(
                REPLICATE_MODEL,
                input={
                    "human_img": current_image_url,
                    "garm_img": garment_url,
                    "garment_des": description,
                    "category": MODEL_CATEGORIES[cat],
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
        storage.storage_upload(f"outputs/{uid}/{result_filename}", resp.content, "image/png")
        row = storage.db_insert("history", {"filename": result_filename, "garment_desc": garment_desc, "user_id": uid})
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not save the result: {exc}"}), 502

    return jsonify(with_image_url(row, "outputs"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
