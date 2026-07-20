# Fresh Checkout Runbook

This runbook is the target path for getting from a clean checkout to a dogfoodable local WatchSignal session in under 15 minutes.

It assumes a local development machine with Node.js 22.6 or newer, pnpm, Python, and the repo-local uv helper available.

## 1. Install Dependencies

From the repo root:

```sh
pnpm install
```

If dependencies are already installed, this should be quick.

## 2. Check Local Readiness

Run the Beta Readiness preflight:

```sh
pnpm beta:preflight
```

Warnings are acceptable when they describe optional live-provider credentials.

Failures should be fixed before dogfooding.

## 3. Run The Project Gate

Run the main local validation gate:

```sh
pnpm beta:check
```

This runs the preflight plus the API test and compile gate.

## 4. Start The Backend

Use a local SQLite path when you want persistent local state:

```sh
MOVIE_NIGHT_MEDIATOR_SQLITE_PATH=../../data/movie_night_mediator.sqlite3 \
  node scripts/run_api_uv.mjs run uvicorn movie_night_mediator.api.main:app --reload --host 0.0.0.0 --port 8000
```

The runner reuses an available `uv` executable or installs the pinned version under the ignored `.tools/` directory on first use.

For an isolated dogfood run, prefer the mobile smoke command in step 6 because it creates a temporary database automatically.

## 5. Start The Web App

In a second terminal:

```sh
API_BASE_URL=http://127.0.0.1:8000 pnpm dev:web
```

Open:

```text
http://localhost:3000
```

## 6. Run The Backend-Backed Mobile Dogfood Smoke

From the repo root:

```sh
pnpm beta:dogfood
```

This runs the phone-sized pass-the-phone flow with a temporary backend database.

On this Mac, direct headless Chrome can fail.

When that happens, start Chrome through macOS first and point the smoke at its DevTools endpoint:

```sh
/usr/bin/open -na 'Google Chrome' --args --headless=new --remote-debugging-port=60420 --user-data-dir=/private/tmp/movie-night-chrome-smoke-60420 --disable-gpu --no-first-run --no-default-browser-check about:blank
MOBILE_UX_SMOKE_EXPECT_API=1 MOBILE_UX_SMOKE_DEBUGGING_URL=http://127.0.0.1:60420 pnpm smoke:ux:mobile
```

## 7. Optional Live TMDb Review

Live TMDb mode is optional for normal local dogfood.

Set one credential in your shell or `.env`:

```sh
TMDB_READ_ACCESS_TOKEN=...
```

or:

```sh
TMDB_API_KEY=...
```

Then start the web app with:

```sh
MOVIE_NIGHT_RECOMMENDATION_SOURCE=live_tmdb API_REQUEST_TIMEOUT_MS=15000 pnpm dev:web
```

Use live mode only when the goal is to review live candidate quality or poster behavior.
