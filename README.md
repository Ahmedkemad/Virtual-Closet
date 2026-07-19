# Virtual Closet

A small personal virtual try-on app. Save a photo of yourself and photos of
tops and bottoms once, then mix and match a full outfit to see what
it looks like on you without re-uploading each time — your library is saved
permanently until you delete something yourself. The **Try It On** tab is
for picking a photo and an outfit; the **My Closet** tab is for adding and
organizing everything you've saved. Supports multiple people sharing one
deployment, each with their own private, invite-gated account and closet.
Uses a hosted AI try-on model via [Replicate](https://replicate.com), stores
your photos in a free [Supabase](https://supabase.com) project, and can be
installed on your iPhone as a home-screen app.

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
    category text not null default 'top',
    created_at timestamptz not null default now()
  );

  create table history (
    id uuid primary key default gen_random_uuid(),
    filename text not null,
    garment_desc text default '',
    created_at timestamptz not null default now()
  );
  ```
- Set up accounts so multiple people can share this app, each with their own
  private closet:
  - In **SQL Editor** → **New query**, paste and run:
    ```sql
    alter table people add column user_id uuid not null;
    alter table garments add column user_id uuid not null;
    alter table history add column user_id uuid not null;

    alter table people enable row level security;
    alter table garments enable row level security;
    alter table history enable row level security;

    create policy "individual access" on people
      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
    create policy "individual access" on garments
      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
    create policy "individual access" on history
      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
    ```
  - In the left sidebar, click **Authentication** → **Providers** → **Email**,
    and turn **off** "Confirm email" — this lets people log in right after
    signing up without needing a working confirmation email.
- In the left sidebar, click the gear icon (**Project Settings**) → **API**.
  Copy the **Project URL**, the **service_role** secret key, and the
  **anon** (or "publishable") key — you'll paste all three in step 4.

> **Already have a Supabase project from before today?** See "Upgrading an
> existing deployment" near the bottom of this file — you have existing data
> that needs a slightly different migration path than a brand-new setup.

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
  **Environment** tab after creation), add all six:
  - `REPLICATE_API_TOKEN` = the token from step 1
  - `SUPABASE_URL` = the Project URL from step 2
  - `SUPABASE_SERVICE_KEY` = the service_role key from step 2
  - `SUPABASE_ANON_KEY` = the anon/publishable key from step 2
  - `FLASK_SECRET_KEY` = any long random string (this signs login sessions —
    pick something like a 40+ character random string; it just needs to be
    secret and stay the same over time)
  - `INVITE_CODE` = any word or phrase you make up — you'll share this with
    whoever you want to be able to sign up (it's the only thing standing
    between a random visitor and creating an account on your Replicate bill)
- Click **Deploy** (or **Create Web Service**). Wait a few minutes for the
  build to finish — Render gives you a URL like
  `https://virtual-closet-xxxx.onrender.com`.

### 5. Use it

Open that URL on your phone or laptop.

- The first time, click **Sign up**, enter the invite code from step 4,
  and pick your own email + password. Everyone who wants their own private
  closet does this once, using the same invite code. After that, the app
  stays logged in on that device for months — no need to log in again each
  time you open it.
- In **My Closet**, click **+ Add** to save a photo of yourself, and **+
  Add** under Tops/Bottoms for each clothing item — they're saved
  permanently so you just tap to pick them next time. Hover (or tap, on
  mobile) a saved photo to see a **×** button to delete it for good.
- In **Try It On**, pick your photo and a top and/or bottom (at least one
  required), then click **Try it on** to see the outfit composited onto
  your photo.
- Everyone's closet is completely private — nobody can see or touch anyone
  else's saved photos, garments, or try-on history, even though you're all
  sharing the same app and the same Replicate/Supabase bill.

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
3. Copy `.env.example` to `.env` and fill in all six values:
   ```bash
   cp .env.example .env
   # edit .env and set REPLICATE_API_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_KEY,
   # SUPABASE_ANON_KEY, FLASK_SECRET_KEY, and INVITE_CODE
   ```
4. Run the app:
   ```bash
   python app.py
   ```
5. Open http://localhost:5000.

## Upgrading an existing deployment to multi-user accounts

If you already had this app running with photos saved before accounts
existed, those rows have no owner yet. Here's the exact sequence to add
accounts without losing anything:

1. In Supabase **SQL Editor** → **New query**, run this (note: no
   `not null` yet, since your tables already have rows without a user_id):
   ```sql
   alter table people add column user_id uuid;
   alter table garments add column user_id uuid;
   alter table history add column user_id uuid;

   alter table people enable row level security;
   alter table garments enable row level security;
   alter table history enable row level security;

   create policy "individual access" on people
     for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
   create policy "individual access" on garments
     for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
   create policy "individual access" on history
     for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
   ```
2. In **Authentication** → **Providers** → **Email**, turn **off**
   "Confirm email".
3. In **Project Settings** → **API**, copy the **anon** (or "publishable")
   key.
4. In Render → your service → **Environment**, add:
   - `SUPABASE_ANON_KEY` = the key from step 3
   - `FLASK_SECRET_KEY` = any long random string
   - `INVITE_CODE` = any word you choose
   Save — Render redeploys with the new code and env vars.
5. Once it's live, go to your app URL, click **Sign up**, and create your
   own account with the invite code from step 4. This is what makes your
   existing photos yours again.
6. In Supabase, go to **Authentication** → **Users**, find the account you
   just created, and copy its **UID**.
7. Back in **SQL Editor**, run (with your real UID pasted in):
   ```sql
   update people set user_id = 'paste-your-uid-here' where user_id is null;
   update garments set user_id = 'paste-your-uid-here' where user_id is null;
   update history set user_id = 'paste-your-uid-here' where user_id is null;
   ```
8. Refresh the app — your existing photos and history should be back,
   now owned by your account.
9. Optional cleanup, once you're sure everything looks right:
   ```sql
   alter table people alter column user_id set not null;
   alter table garments alter column user_id set not null;
   alter table history alter column user_id set not null;
   ```

Anyone else who wants their own closet just goes to `/signup` on the same
app URL with the same invite code — they'll start with a completely empty,
private closet of their own.

## Notes

- The try-on model (idm-vton) only handles one garment at a time, and needs
  to know whether it's upper-body or lower-body clothing (the app passes
  this automatically based on whether you added it under Tops or Bottoms).
  To composite a full outfit, the app calls the model once per selected
  item, feeding each result back in as the base photo for the next item
  (top, then bottom). This works well for two items, but quality can
  degrade slightly on the second pass (minor drift in pose/background).
- Shoes aren't supported — idm-vton only has categories for upper-body,
  lower-body, and dresses, with no footwear option, so there's no reliable
  way to try on shoes with this model.
- Each try-on with N items costs N times the usual Replicate charge, since
  it's N sequential model calls.
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
