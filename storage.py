import os

import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "closet")


def is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def _headers(content_type: str | None = None) -> dict:
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def db_select(table: str) -> list:
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=_headers(),
        params={"select": "*", "order": "created_at.desc"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def db_insert(table: str, row: dict) -> dict:
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers={**_headers("application/json"), "Prefer": "return=representation"},
        json=row,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()[0]


def db_delete(table: str, item_id: str) -> dict | None:
    resp = requests.delete(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers={**_headers("application/json"), "Prefer": "return=representation"},
        params={"id": f"eq.{item_id}"},
        timeout=15,
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def storage_upload(path: str, data: bytes, content_type: str) -> None:
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{path}",
        headers=_headers(content_type),
        data=data,
        timeout=30,
    )
    resp.raise_for_status()


def storage_delete(path: str) -> None:
    resp = requests.delete(
        f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}",
        headers=_headers("application/json"),
        json={"prefixes": [path]},
        timeout=15,
    )
    resp.raise_for_status()


def public_url(path: str) -> str:
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{path}"
