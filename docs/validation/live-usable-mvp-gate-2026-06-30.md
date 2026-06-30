# Live-Usable MVP Gate

Date: 2026-06-30.

Issue: GitHub #26.

## Scope

This validation records the final MVP readiness pass after the live TMDb candidate source and backend-backed couch flow were merged.
It does not start MVP plus 1 LLM interpretation.
It does not add a paid provider, hosted deployment, separate-phone sessions, live critic scores, or a live poster provider.

## Current Status

The code-first app is live-candidate ready, but the live-usable MVP gate still needs a normal local browser or real-phone click-through outside this Codex browser-launch environment.
The backend can fetch live TMDb candidates and score a five-title shortlist.
The backend-backed couch flow can run end to end against isolated SQLite with recommendation snapshot evidence.
The web flow can request live TMDb candidates by starting the Next.js server with `MOVIE_NIGHT_RECOMMENDATION_SOURCE=live_tmdb`.
The remaining gate is founder-facing interaction proof in a normal browser or phone-sized browser environment.

## Validation Passed In Codex

`apps/api/.venv/bin/python -m unittest discover apps/api/tests` passed with 97 tests.

`python3 scripts/couch_flow_smoke.py` passed against isolated temporary SQLite storage.

`python3 scripts/couch_flow_smoke.py --live-fake-candidates` passed against isolated temporary SQLite storage with persisted recommendation snapshot evidence.

`apps/api/.venv/bin/python -m compileall -q apps/api/src scripts` passed.

`python3 scripts/tmdb_candidate_source_smoke.py` passed with 10 live candidates, 8 safe picks, and a five-title shortlist.

`NEXT_TELEMETRY_DISABLED=1 node node_modules/.pnpm/next@16.2.9_react-dom@19.2.7_react@19.2.7__react@19.2.7/node_modules/next/dist/bin/next build` passed from `apps/web`.

The web app was rebuilt after adding the live-source switch.

With FastAPI running against isolated SQLite and local TMDb credentials, the production web API route returned a live five-title shortlist through `/api/recommendations/shortlist`.

The live web-proxy smoke returned source ids `tmdb:278`, `tmdb:238`, `tmdb:1398050`, `tmdb:680`, and `tmdb:755898`.

The first live web-proxy title was `The Shawshank Redemption`.

The first web-proxy attempt exposed that the default 2500ms proxy timeout was too short for a live TMDb candidate fetch.
The web proxy now uses a longer default timeout when `MOVIE_NIGHT_RECOMMENDATION_SOURCE=live_tmdb`, with `API_REQUEST_TIMEOUT_MS` available as an override.

## Browser Smoke Result In Codex

`pnpm smoke:ux:mobile` did not reach the product flow because pnpm attempted registry verification and npm attestation checks, then failed DNS resolution for `registry.npmjs.org`.

Starting the installed Next.js server directly bypassed the package-manager preflight and served the app locally.

`MOBILE_UX_SMOKE_URL=http://127.0.0.1:3100 node scripts/mobile_pass_the_phone_ux_smoke.mjs` then failed before page interaction because Brave exited with `SIGABRT` before exposing a DevTools endpoint.

The same command with `MOBILE_UX_SMOKE_BROWSER_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"` also failed before page interaction because Chrome exited with `SIGABRT` before exposing a DevTools endpoint.

The Codex in-app browser control surface was not available in this session, so there was no fallback automated browser surface to use.

These failures are recorded as environment and harness blockers, not observed product-flow failures.

## Required Normal-Browser Gate

Run the final click-through from a normal local browser or a phone on the same network.

Use a backend with TMDb credentials available.

Start the web app with `MOVIE_NIGHT_RECOMMENDATION_SOURCE=live_tmdb`.

Click through Launch, Setup, first Reaction pass, Handoff, second Reaction pass, Results, outcome capture, post-watch feedback, and debug-history evidence.

Record whether the visible shortlist used live TMDb-backed source ids such as `tmdb:...`.

Record whether debug history shows recommendation snapshot evidence instead of missing candidate inputs or group scores.

## Decision

The repo should not yet declare the code-first app fully live-usable MVP until the normal-browser or real-phone click-through is recorded.
It is backend-live-ready and demo-complete.
It is one manual phone/browser validation pass away from closing the live-usable MVP gate.
