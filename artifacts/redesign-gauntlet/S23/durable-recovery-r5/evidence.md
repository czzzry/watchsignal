# Durable private-transition recovery R5 evidence

## Claim

The final local WatchSignal tree preserves private progress through the deployment-style failures covered by the durable recovery contract and completes the ordinary household journey.

## Contract

API-backed couple recovery is durable, tenant-scoped, strict, body-only, idempotent, expiring, and consumable only after safe result acknowledgement or explicit reset.

Solo and disconnected paths do not claim refresh recovery.

## Boundary

The recovery module owns workflow persistence, reconciliation, expiry, and safe projections.

The shared-session service owns canonical session transitions and taste-memory side effects.

The browser client owns the opaque checkpoint and safe restore navigation.

Recommendation scoring and accepted visual direction are unchanged.

## Local release evidence

- Tooling tests passed 5 of 5.
- The full web suite passed 252 of 252 tests.
- The full API suite passed 418 tests with seven hosted-only tests skipped in the ordinary run.
- API compilation passed.
- TypeScript passed.
- The production build passed and generated 36 pages.
- The old process-local vault route is absent from the production manifest.
- Hosted preflight passed.
- Beta preflight passed with configuration and dirty-worktree warnings only.
- The hosted PostgreSQL multi-process and crash-window suite passed 7 of 7 tests.
- MVP+4 passed its preflight, full checks, build, recommendation evaluation, and live dogfood journey.
- MVP+5 passed its preflight, full checks, build, household-memory evaluation, and live dogfood journey.
- The final live 390 by 844 journey completed setup, both private passes, durable handoff, matching, ranked result, review evidence, watchlist, watched outcome, both profile ratings, taste memory, recent-night history, and restart.
- S06 earned independent ACCEPT at 37 of 40 with Functional fidelity at 5 of 5.
- S07 earned independent ACCEPT at 36 of 40 with Functional fidelity at 5 of 5.

## Resource behavior

All heavy gates ran sequentially at reduced process priority.

Each smoke runner closed its temporary web server, API process, and browser.

No task-owned preview server, browser automation process, test watcher, or build remains active.

## Evidence limits

The local hosted proof uses two fresh API processes and stateless web adapters against the configured PostgreSQL database.

It does not replace the required deployed Vercel and Neon cold-invocation trace.

The redesign worktree is still uncommitted and must become an intentional founder-approved checkpoint before publication.

## Decision

Local implementation and release evidence are complete.

Production publication remains held only for the deployed Vercel and Neon trace and the founder-owned Git checkpoint.
