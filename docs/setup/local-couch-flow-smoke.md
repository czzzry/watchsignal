# Local Couch Flow Smoke

This smoke test proves that the local backend can run the pass-the-phone couch flow against an isolated SQLite database.
It does not call external services.
It does not mutate `data/movie_night_mediator.sqlite3` or any real household data.

## Run It

From the repo root:

```sh
python3 scripts/couch_flow_smoke.py
```

If the plain interpreter does not have the API dependencies active, run it with the backend environment instead:

```sh
apps/api/.venv/bin/python scripts/couch_flow_smoke.py
```

In a Treehouse worktree that shares the parent checkout's local `uv` install, this form also works after dependencies are available in the local cache:

```sh
UV_CACHE_DIR=/Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/cache/uv /Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/uv/bin/uv run --project apps/api python scripts/couch_flow_smoke.py
```

## What It Proves

The script creates a temporary SQLite file and wires every backend store to that file.
It calls the FastAPI route functions in process with the same Pydantic payload models used by the API.
It seeds the default fallback setup profiles, `husband` and `wife`.
It completes onboarding for both profiles.
It creates a five-title shared session.
It submits the first pass of reactions for `husband`.
It advances the handoff.
It submits the second pass of reactions for `wife`.
It verifies the reranked result and best pick.
It saves one post-watch feedback row.
It verifies debug history evidence for the persisted session, reactions, rerank, best pick, post-watch feedback, and currently unavailable score inputs.

## Expected Output

```text
Couch flow smoke passed.
Temporary SQLite DB was isolated at: /tmp/.../smoke.sqlite3
```

The temporary directory is removed when the script exits.
If any route, state transition, persistence step, or debug-history assertion fails, the script exits with a non-zero status and prints the failed expectation.
