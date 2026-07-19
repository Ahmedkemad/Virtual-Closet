import os

import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


def is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


def _extract_error(data: dict) -> str:
    return data.get("msg") or data.get("error_description") or data.get("error") or data.get("message") or "Something went wrong."


def signup(email: str, password: str) -> str:
    """Create a Supabase Auth user and return their user id."""
    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=15,
    )
    data = resp.json()
    if resp.status_code >= 400:
        raise ValueError(_extract_error(data))
    user = data.get("user") or data
    if not user or not user.get("id"):
        raise ValueError("Could not create account.")
    return user["id"]


def login(email: str, password: str) -> str:
    """Verify email/password against Supabase Auth and return the user id."""
    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=15,
    )
    data = resp.json()
    if resp.status_code >= 400:
        raise ValueError(_extract_error(data))
    user = data.get("user") or {}
    if not user.get("id"):
        raise ValueError("Could not log in.")
    return user["id"]
