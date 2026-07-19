# Virtual Closet

A small personal virtual try-on app. Upload a photo of yourself and a photo of a
garment, and see what it looks like on you. Runs locally, uses a hosted
AI try-on model via [Replicate](https://replicate.com), and keeps a local
history of your try-ons.

## How it works

This app doesn't train its own model — it calls a pretrained virtual try-on
model (default: [`cuuupid/idm-vton`](https://replicate.com/cuuupid/idm-vton))
hosted on Replicate. That's the practical route for personal use: these
models need large paired datasets and heavy GPU training that isn't worth
reproducing for individual use.

## Setup

1. Create a [Replicate](https://replicate.com) account and generate an API
   token from https://replicate.com/account/api-tokens.
2. Install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your token:
   ```bash
   cp .env.example .env
   # edit .env and set REPLICATE_API_TOKEN
   ```
4. Run the app:
   ```bash
   python app.py
   ```
5. Open http://localhost:5000, upload your photo and a garment photo, and
   click "Try it on".

## Notes

- Uploaded photos and results are saved locally under `static/uploads/` and
  `static/outputs/` (git-ignored) — nothing is stored except on your machine
  and on Replicate's servers during processing.
- Each try-on costs a small fraction of a dollar in Replicate compute
  (check current pricing on the model's Replicate page).
- If the model's input schema changes, adjust the `input=` dict in
  `app.py`'s `/try-on` route to match the fields shown on the model's
  Replicate page. You can swap models entirely via the `REPLICATE_MODEL`
  env var.
- For full privacy with no per-image cost, you can self-host the same class
  of model (e.g. IDM-VTON or OOTDiffusion) on your own GPU — that requires
  more setup and a decent GPU (10GB+ VRAM) and isn't wired up here.
