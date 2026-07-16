# Hosted Android production validation

Date: 2026-07-16.

Status: Passed for the one-phone Android pilot.

## Claim

WatchSignal can run from Vercel as an installable Android web app without depending on the founder's computer.

The hosted app should retain the migrated household data, authenticate with a phone-friendly household passphrase, persist real user actions in Neon, and receive future GitHub-to-Vercel updates automatically.

## Contract

The web app is served from `https://watchsignal-web.vercel.app`.

The private API is served from `https://watchsignal-api.vercel.app` and requires the shared service token except for health checks.

The browser session uses a signed, secure, HTTP-only, same-site cookie with a 90-day lifetime.

Neon PostgreSQL is the hosted system of record.

The PWA manifest uses standalone display mode and the service worker uses network-only update behavior.

## Boundary

Vercel owns web and API execution.

Neon owns hosted persistence.

TMDb owns the live candidate feed.

The web app owns household authentication and forwards authenticated requests to the private API.

The Android installation remains a browser-installed PWA and does not require a Play Store release for this pilot.

## Production behavior exercised

The validation used a 412 by 915 Android-sized browser viewport.

The password screen rejected an incorrect passphrase, supported show and hide controls, accepted the correct passphrase, and kept the new tab signed in.

The PWA manifest, 192-pixel icon, 512-pixel icon, standalone start URL, and network-only service worker all loaded from production.

The production API returned five live TMDb candidates in four seconds during the final direct smoke check.

A complete two-person pass-the-phone round used the same five live titles for both participants, saved both reaction passes, produced a shared result, and showed `Live TMDb` as the result source.

The final result had no unsynced-session warning.

Adding the result to the watchlist persisted it in Neon and the read API returned it after the interaction.

Taste Lab loaded the stored high-signal queue, saved one rating, removed the rated title from the queue, and increased the stored rating totals.

Signing out, rejecting a wrong passphrase, signing back in, and reopening the app all completed on production.

A fresh app open resolved the saved Cezary and Husband household pair and reached `Start first pass` after the readiness check completed.

Opening Taste Lab used the saved Cezary profile and did not create or activate a test profile.

The production build footer changed as promoted commits deployed, proving that the installed PWA can receive a new network-served build without reinstallation.

## Bugs found and fixed during production click-throughs

The FastAPI deployment initially tried to create an unused SQLite directory in PostgreSQL mode on Vercel's read-only filesystem.

The store initialization now skips SQLite path preparation when `DATABASE_URL` selects PostgreSQL.

The TMDb candidate path initially made sequential details and provider calls and allowed one timeout to abort the whole round.

The adapter now requests providers with movie details, normalizes transport failures, skips isolated slow candidates, and continues building the remaining pool.

The web app initially fell into an unsaved demo round after a live-provider failure.

It now creates a synced backup-catalog session so reactions, history, outcomes, and watchlist behavior remain available during a temporary TMDb failure.

Taste Lab initially created and activated an `Alex - tester` profile merely by opening the page.

Taste Lab now reads the existing household setup and defaults to its saved active profile without mutating setup.

The temporary test-profile setup mutation was restored to Cezary and Husband after diagnosis.

## Data migration evidence

The migration started only after the Neon schema was confirmed empty.

The SQLite database was backed up before applying the migration.

All 21 migrated table counts matched between SQLite and Neon after the transaction committed.

The migrated data included 3 onboarding profiles, 56 recommendation snapshots, 8 shared sessions, 250 Taste Lab candidates, 163 Taste Lab ratings, 194 taste memory events, and 2 watchlist entries before production click-throughs added new dogfood evidence.

## Automated evidence

`pnpm hosted:check` passed on the final implementation.

The final local gate ran 342 backend tests, API compilation, hosted preflight checks, service-worker syntax validation, the production Next.js build, and TypeScript validation.

GitHub Actions passed both MVP check jobs.

The Vercel API and web deployment checks passed.

## Decision

Promote the hosted Android pilot for one-phone use.

The founder still owns the final physical-phone install and real household acceptance decision.

Two-phone concurrency, Play Store packaging, push notifications, and offline data mutation remain outside this pilot decision.

The production click-through intentionally added one watchlist item and one Taste Lab rating as dogfood evidence.
