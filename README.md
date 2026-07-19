# Virtual Closet

A small personal virtual try-on app. Save a photo of yourself and photos of
garments once, then mix and match them to see what looks like on you without
re-uploading each time — your library is saved permanently until you delete
something yourself. Uses a hosted AI try-on model via
[Replicate](https://replicate.com), stores your photos in a free
[Supabase](https://supabase.com) project, and can be installed on your
iPhone as a home-screen app.

## How it works

This app doesn't train its own model — it calls a pretrained virtual try-on
model (default: [`cuuupid/idm-vton`](https://replicate.com/cuuupid/idm-vton))
hosted on Replicate. That's the practical route for personal use: these
models need large paired datasets and heavy GPU training that isn't worth
reproducing for individual use.

Photos and the try-on history are stored in Supabase (a free hosted
database + file storage), not on Render's own disk — Render's free plan has
no permanent disk, so anything saved only there gets wiped on every
redeploy. Supabase keeps your library intact forever, independent of the
app's hosting.

## Setup — no coding required (hosted on Render + Supabase)

This takes three sign-ups (Replicate, Supabase, Render), all free, all just
clicking through web pages.

### 1. Get a Replicate API token

This pays for each try-on, a few cents each.

- Go to https://replicate.com and sign up (you can use your Google/GitHub account).
- Go to https://replicate.com/account/api-tokens and click **Create token**.
- Copy the token somewhere — you'll paste it in step 3.

### 2. Set up Supabase (free permanent storage for your photos)

- Go to https://supabase.com and sign up (GitHub sign-in works).
- Click **New project**. Pick any name (e.g. "virtual-closet"), pick a
  database password (save it somewhere, though this app won't need it
  directly), pick any region, click **Create new project**. Wait a minute
  or two for it to finish setting up.
- In the left sidebar, click **Storage** → **New bucket**. Name it exactly
  `closet`, toggle **Public bucket** ON, click **Create bucket**.
- In the left sidebar, click **SQL Editor** → **New query**. Paste this
  exactly, then click **Run**:
  ```sql
  create table people (
    id uuid primary key default gen_random_uuid(),
    filename text not null,
    label text default '',
    created_at timestamptz not null default now()
  );

  create table garments (
    id uuid primary key default gen_random_uuid(),
    filename text not null,
    label text default '',
    created_at timestamptz not null default now()
  );

  create table history (
    id uuid primary key default gen_random_uuid(),
    filename text not null,
    garment_desc text default '',
    created_at timestamptz not null default now()
  );
  ```
- In the left sidebar, click the gear icon (**Project Settings**) → **API**.
  Copy the **Project URL**, and copy the **service_role** secret key (not
  the "anon" key — the service_role one). You'll paste both in step 4.

### 3. Deploy the app on Render

- Go to https://render.com and sign up using your GitHub account.
- Click **New +** → **Web Service**.
- Choose **Build and deploy from a Git repository**, then connect/select
  the `Virtual-Closet` repository and pick the
  `claude/virtual-try-on-clothes-ljc5lf` branch.
- Render auto-detects the build/start settings from `render.yaml` in this
  repo. Just confirm, keeping the **Free** instance type.

### 4. Add your environment variables

- When prompted for environment variables (or under the service's
  **Environment** tab after creation), add all three:
  - `REPLICATE_API_TOKEN` = the token from step 1
  - `SUPABASE_URL` = the Project URL from step 2
  - `SUPABASE_SERVICE_KEY` = the service_role key from step 2
- Click **Deploy** (or **Create Web Service**). Wait a few minutes for the
  build to finish — Render gives you a URL like
  `https://virtual-closet-xxxx.onrender.com`.

### 5. Use it

Open that URL on your phone or laptop. Click **+ Add** under "Your photo"
to save a photo of yourself once, and **+ Add** under "Garment" for each
clothing item — they're saved permanently so you just tap to pick them next
time. Hover (or tap, on mobile) a saved photo to see a **×** button to
delete it for good.

Note on the Render free plan: the service "sleeps" after 15 minutes of no
use, so the first request after a while takes ~30-60 seconds to wake up —
that's normal and doesn't affect your saved photos either way.

## Install it on your iPhone

The app works as an installable home-screen app (no App Store needed):

1. Open your Render app URL in **Safari** on your iPhone (must be Safari,
   not Chrome).
2. Tap the **Share** icon (square with an arrow) in the toolbar.
3. Scroll down and tap **Add to Home Screen**, then tap **Add**.
4. A "Virtual Closet" icon appears on your home screen — opening it launches
   full-screen, without Safari's address bar, like a normal app.

## Setup — running it yourself in a terminal (optional, for developers)

1. Create Replicate and Supabase accounts and follow steps 1 and 2 above to
   get a Replicate token and Supabase project/bucket/tables.
2. Install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in all three values:
   ```bash
   cp .env.example .env
   # edit .env and set REPLICATE_API_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_KEY
   ```
4. Run the app:
   ```bash
   python app.py
   ```
5. Open http://localhost:5000.

## Notes

- Photos and try-on history live in your Supabase project (Storage bucket
  `closet` + the `people`/`garments`/`history` tables) — nothing is stored
  on Render's disk, so it all survives redeploys, sleeps, and restarts. It's
  only ever wiped if you delete items yourself or delete the Supabase
  project.
- If your app goes completely unused for 7+ days, Supabase's free tier
  pauses the project. It automatically resumes (data intact) within about
  30 seconds of the next request — you may see a brief error on the very
  first load after a long break; just refresh.
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
