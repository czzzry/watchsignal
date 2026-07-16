# Hosted Android Local Readiness - 2026-07-16

## Status

Local implementation is ready for external Vercel and Neon integration.
Hosted promotion remains on hold because no external project, PostgreSQL database, private secret, real-data import, or physical Android installation was created during the AFK run.

## Claim

WatchSignal can retain its existing phone-first product behavior while becoming an installable Android web app backed by hosted services and durable PostgreSQL data.

## Contract

The Android installation contract is a standalone web manifest with 192-pixel and 512-pixel icons, portrait orientation, HTTPS delivery, and a network-only service worker.
The access contract is one household passphrase, a signed HTTP-only session cookie, and a separate server-to-server API token.
The storage contract selects SQLite for local development and tests and selects PostgreSQL when `DATABASE_URL` is present without a SQLite override.
The migration contract performs an inspection-only run by default, creates a SQLite backup before applying, refuses to replace non-empty PostgreSQL data without an explicit flag, and compares every migrated table count.

## Boundary

The Next.js application owns browser installation, household access, and authenticated browser-to-API proxying.
FastAPI owns application routes and rejects non-health requests that lack the configured service token.
Storage adapters own database dialect selection without changing application-service or scoring contracts.
Recommendation scoring, candidate generation, tonight intent, and the pass-the-phone state machine remain unchanged.

## Behavior

An unauthenticated hosted request redirects to the household login.
An incorrect passphrase remains on the login screen with a clear error.
A correct passphrase creates a secure remembered session and opens the existing WatchSignal flow.
The session cookie is unavailable to browser JavaScript.
Server-rendered setup loading and same-origin API requests carry the backend service token.
Signing out removes the session and returns to login.
The installed shell checks for updated service-worker code without caching application responses for offline use.

## Evidence

`pnpm hosted:check` passed.
The gate included the hosted Android asset preflight, 336 API tests, Python compilation, and the production Next.js build.
The public-data hygiene check passed.
The migration command completed an inspection-only run against a temporary SQLite fixture without contacting PostgreSQL.
The Vercel FastAPI entrypoint imported successfully through the locked application environment.

A production-mode browser click-through ran at a phone-sized viewport against isolated local SQLite storage.
The click-through verified redirect to login, incorrect-passphrase rejection, correct-passphrase acceptance, authenticated setup loading, registered manifest, registered service worker, an HTTP-only cookie, the existing onboarding screen, and sign-out.
The browser console contained no errors.

The existing full couch-flow smoke built and started both applications but its bundled Brave process exhausted browser virtual memory before interaction began.
That failure is consistent with the repository's documented local browser-launch limitation and does not show an application assertion failure.
The separate production-mode browser click-through proves the new hosted access path, but it does not replace the still-required full physical-phone acceptance.

No live PostgreSQL integration test has run because no Neon project or local PostgreSQL server was available.
The compatibility layer is covered by existing SQLite behavior tests and focused SQL translation tests, but live PostgreSQL behavior remains unproven.

## Decision

Promote the local implementation to external integration review.
Do not migrate real household data or claim the Android outcome complete until Vercel deployment, live Neon persistence, backup and restore, automatic production update, and physical Android installation all pass.

## Open risks

- Vercel's Python runtime may expose a packaging or function-limit issue not reproducible locally.
- Free-tier cold starts may exceed an acceptable movie-night wait.
- The PostgreSQL compatibility layer needs live Neon evidence across setup, sessions, Taste Lab, history, watchlist, feedback, and outcomes.
- The free Neon recovery window may be too short for comfortable household use.
- Chrome installation and update behavior still require the founder's real Android phone.
