# WatchSignal

WatchSignal finds where your movie tastes overlap and gives you picks that keep everyone happy.

![WatchSignal showcase](docs/assets/watchsignal-showcase.gif)

## What It Is

WatchSignal is a phone-first web app for picking a movie together.
Each person gets a private pass through the same shortlist, then the app combines both reactions into a shared result with a clear reason for why that pick won.

The product goal is simple: less couch debate, more watching.

## Why It Is Interesting

- It turns a fuzzy human problem into a structured decision flow.
- It uses live TMDb metadata and poster art for real movie candidates.
- It keeps recommendation logic separate from the web UI, API layer, and persistence.
- It has a pass-the-phone interaction model designed for one couch and one shared decision.
- It explains the final pick instead of only showing a score.

## MVP Status

The MVP is functionally complete.
The app can run locally, collect household taste setup, fetch or fall back to movie candidates, record pass-the-phone reactions, score a shared pick, and show why the result won.

The showcase route at `/showcase` is intentionally staged for portfolio review.
It presents the product promise in a cleaner trailer format while the main app route remains the working MVP flow.

## Tech Stack

- Next.js app router frontend in `apps/web`
- FastAPI backend in `apps/api`
- SQLite persistence for local MVP state
- Python recommendation and scoring code
- TMDb integration for live movie metadata and poster art
- GitHub Actions checks for the MVP gate

## Local Development

Run the FastAPI backend from one terminal:

```sh
cd apps/api
../../.tools/uv/bin/uv run uvicorn movie_night_mediator.api.main:app --reload --host 0.0.0.0 --port 8000
```

Run the Next.js web app from another terminal:

```sh
env npm_config_cache="$PWD/.tools/npm-cache" PNPM_HOME="$PWD/.tools/pnpm" XDG_CACHE_HOME="$PWD/.tools/cache" npm exec --yes --package=pnpm@10 -- pnpm dev:web
```

Open `http://localhost:3000`.

To view the recruiter showcase, open:

```text
http://localhost:3000/showcase
```

## Validation

Backend checks:

```sh
cd apps/api
../../.tools/uv/bin/uv run python -m unittest discover -s tests
../../.tools/uv/bin/uv run python -m compileall -q src tests
```

Frontend build:

```sh
env npm_config_cache="$PWD/.tools/npm-cache" PNPM_HOME="$PWD/.tools/pnpm" XDG_CACHE_HOME="$PWD/.tools/cache" npm exec --yes --package=pnpm@10 -- pnpm --dir apps/web build
```

## Notes

This repository began as the code-first companion to a Movie Night Mediator prototype.
Some older planning documents still use that working title.
The public product identity is now WatchSignal.

Local `.env` credentials are required for live TMDb mode.
Secrets are intentionally ignored by Git and should not be committed.
