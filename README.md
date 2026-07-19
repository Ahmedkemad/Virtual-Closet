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

## Setup — no coding required (hosted on Render)

This is the easiest way to use the app: click through two website sign-ups,
and you get a link you can open on your phone or computer any time.

1. **Get a Replicate API token** (this pays for each try-on, a few cents each):
   - Go to https://replicate.com and sign up (you can use your Google/GitHub account).
   - Go to https://replicate.com/account/api-tokens and click "Create token".
   - Copy the token somewhere — you'll paste it in step 3.
2. **Deploy the app on Render** (this hosts the app and gives you a web link):
   - Go to https://render.com and sign up using your GitHub account.
   - Click **New +** → **Web Service**.
   - Choose **Build and deploy from a Git repository**, then connect/select
     the `Virtual-Closet` repository and pick the
     `claude/virtual-try-on-clothes-ljc5lf` branch.
   - Render will auto-detect the settings from `render.yaml` in this repo
     (build command, start command, free plan). Just confirm.
3. **Add your Replicate token:**
   - When prompted for the `REPLICATE_API_TOKEN` environment variable (or
     under the service's "Environment" tab after creation), paste the token
     from step 1.
4. Click **Deploy** (or **Create Web Service**). Wait a few minutes for the
   build to finish — Render gives you a URL like
   `https://virtual-closet-xxxx.onrender.com`.
5. Open that URL on your phone or laptop, upload a photo of yourself and a
   photo of a garment, and click "Try it on".

Notes on the free plan: the service "sleeps" after 15 minutes of no use, so
the first request after a while takes ~30-60 seconds to wake up — that's
normal. Uploaded photos and results also get cleared whenever the service
restarts, so treat it as scratch space, not permanent storage.

## Setup — running it yourself in a terminal (optional, for developers)

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
  env var — for community (non-official) models, include the version hash
  after a colon, e.g. `owner/model:abc123...`, or calls will 404.
- For full privacy with no per-image cost, you can self-host the same class
  of model (e.g. IDM-VTON or OOTDiffusion) on your own GPU — that requires
  more setup and a decent GPU (10GB+ VRAM) and isn't wired up here.
