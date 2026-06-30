# Live TMDb Candidate Source Smoke

This smoke verifies the issue #24 candidate-source seam against live TMDb credentials.
It is separate from the mobile browser smoke because the Codex and CI CDP harness can hang before the app flow is reached.
This smoke checks backend candidate sourcing only.

## Prerequisites

Store one TMDb credential locally in `.env`.
Use either `TMDB_READ_ACCESS_TOKEN` or `TMDB_API_KEY`.
Do not commit `.env`.

## Command

Run from the repo root:

```sh
python3 scripts/tmdb_candidate_source_smoke.py
```

If the plain interpreter does not have the API package available, use the backend environment:

```sh
apps/api/.venv/bin/python scripts/tmdb_candidate_source_smoke.py
```

## Expected Result

The command should print JSON with a non-zero `candidateCount`.
When enough Prime Video Germany flatrate English-accessible movies are returned, the `shortlist` should contain five ranked items.
The output must contain only public movie metadata and ranking summaries.
It must not print credentials or private household data.

## Relation To Mobile Smoke

This smoke does not replace `pnpm smoke:ux:mobile`.
The mobile smoke remains the final user-flow proof for issue #26.
If the mobile smoke fails in Codex or CI before a browser is controllable, keep treating that as the known harness caveat until it is reproduced in a normal local browser.
