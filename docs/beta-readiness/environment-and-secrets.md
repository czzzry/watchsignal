# Environment And Secrets

This project should run locally without secrets in demo-safe fixture mode.

Secrets are only needed for optional live-provider checks.

## Required For Local Demo Mode

No secret is required.

SQLite defaults to:

```text
data/movie_night_mediator.sqlite3
```

The backend reads the override:

```text
MOVIE_NIGHT_MEDIATOR_SQLITE_PATH
```

The web app defaults to:

```text
API_BASE_URL=http://127.0.0.1:8000
```

## Optional Live TMDb Mode

Set one of these when reviewing live candidate generation:

```text
TMDB_READ_ACCESS_TOKEN
TMDB_API_KEY
```

The live web path is enabled with:

```text
MOVIE_NIGHT_RECOMMENDATION_SOURCE=live_tmdb
```

For slower live calls, use:

```text
API_REQUEST_TIMEOUT_MS=15000
```

## Optional Taste Lab Web Route

The Taste Lab client can point at a custom backend with:

```text
NEXT_PUBLIC_TASTE_LAB_API_BASE_URL=http://127.0.0.1:8000
```

## Not Currently Required

`TELEGRAM_BOT_TOKEN` is not required for the local mobile web MVP.

`OPENAI_API_KEY` is not required for the current local product flow.

`DATABASE_URL` is not used by the current SQLite-backed local flow.

## Commit Rules

Do not commit `.env`.

Do not commit local SQLite databases.

Do not commit TMDb tokens.

Do not commit generated MovieLens-derived queues unless a later decision explicitly changes the data policy.

Use `.env.example` as the public contract for environment names.
