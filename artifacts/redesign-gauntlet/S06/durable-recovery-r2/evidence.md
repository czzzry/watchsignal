# Durable recovery R2 evidence

## Claim

Private-transition recovery requests reach the durable recovery module without trusting browser-supplied ownership or exposing the recovery token or private payload through URLs, caches, responses, or logs.

## Contract

The browser-facing adapter verifies the signed household session, enforces same-origin JSON requests, and derives the single deployment tenant only from server configuration.

Seal, resume, and consume carry the opaque token only in a JSON request body.

Every recovery response is `Cache-Control: no-store`.

The daily cleanup route requires both the backend service token and a dedicated cron secret and returns only an aggregate deletion count.

## Boundary

The Next.js adapter owns browser authentication, request-shape enforcement, same-origin protection, server-owned tenancy, and fixed public error mapping.

The FastAPI adapter owns strict transport DTOs, service authentication, module adaptation, fixed public errors, and no-store responses.

The transport layer does not own workflow transitions, ranking, browser navigation, or canonical session reconciliation.

The process-local vault remains present but is not promoted and cannot be removed until the later browser cutover is independently accepted.

## Behavior proved in quiet mode

- Missing household password, session secret, backend service token, deployment household identifier, or cron secret fails closed.
- The browser handler verifies the signed session directly and does not assume that the outer proxy ran.
- Cross-origin, non-JSON, oversized, query-bearing, and browser-tenant-bearing requests are rejected before forwarding.
- Recovery tokens are carried only in JSON bodies and never in paths or queries.
- The backend forwarder emits fixed public errors and never reflects an upstream response body, URL, exception, token, ballot, title, or private field.
- Resume responses pass an exact stage-specific allowlist before reaching the browser.
- Movie display responses enforce the same year, genre, URL, public-evidence, matched-person, and penalty rules as the Python domain contract.
- Hostile successful upstream responses containing unsafe URL schemes, private scorer identifiers, oversized evidence, invalid years, or unmatched person evidence are rejected.
- The daily maintenance route validates both secrets, invokes only the bounded purge operation, and returns only `{deleted}`.
- The Vercel schedule invokes only the authenticated maintenance route once per day.
- A founder seal made through one fresh operating-system API process was resumed through a second fresh process against the same hosted PostgreSQL database.
- The hosted test removed its recovery and canonical session rows in its `finally` boundary.

## Validation

- Focused web transport, command, and maintenance suites passed 20 tests.
- Focused API recovery, maintenance, transport, PostgreSQL-registration, and contract-export suites completed 41 tests with 39 passing and two opt-in PostgreSQL tests skipped.
- The opt-in hosted PostgreSQL suite passed both tests in 19.319 seconds.
- The full web suite passed 247 tests.
- The full API suite completed 395 tests with 393 passing and two opt-in PostgreSQL tests skipped.
- API compilation passed.
- TypeScript passed.
- Hosted deployment preflight passed with the recovery household and cleanup-secret requirements active.
- The production web build passed TypeScript, generated 37 static pages, and emitted all recovery and maintenance routes.
- Scoped diff validation passed.

## Decision

The first independent review requested an exact response allowlist and a real cross-process PostgreSQL transport trace.

Both corrections were implemented with focused red-green evidence.

The independent re-review found no material gap and accepted R2.

R2 is promoted.

R3 now owns durable command leasing, stale-worker fencing, canonical session idempotency, exact side-effect counts, and crash-window reconciliation.

This R2 evidence does not claim browser recovery integration or removal of the process-local vault.
