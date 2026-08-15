# Private-transition recovery implementation gate

This plan becomes active only after the founder accepts ADR-002 Option A.

It does not authorize an architecture change on its own.

## Slice R1: strict recovery contract and durable store

### Claim

A recovery record can survive a fresh application process without accepting malformed, oversized, expired, or cross-tenant data.

### Contract

Define the ADR's discriminated `SealCommand`, strict stored snapshot, stage-specific `ResumeProjection`, and exact two-hour access expiry.

Store only a token digest and strictly allowlisted payload.

### Boundary

The `PrivateTransitionRecovery` module owns the three-entry interface, command validation, persistence coordination, expiry, and safe projections.

Its internal store adapter owns SQL row changes but does not own session transitions, recommendation behavior, or browser presentation.

Any single-process canonical-state reconciliation tracers created during R1 are provisional storage behavior only.

They do not satisfy R3 lease ownership, crash-window recovery, side-effect exactness, stale-owner fencing, or multi-process gates.

### Behavior

Seal, resume, and consume behave identically through the module interface on SQLite and PostgreSQL adapters.

### Required evidence

- Red-green discriminated-command, schema, projection, and parser tests through only `seal`, `resume`, and `consume`.
- Adapter-only portability tests below the module seam.
- Persistence across two fresh store instances sharing one database.
- Same command ID and fingerprint returns the recorded result.
- Same command ID and different fingerprint conflicts without mutation.
- A valid new command at the next revision advances once.
- Exact expiry boundary and no read-based extension.
- Consume twice with the same result.
- Consume transaction directly proves command rows and the recovery row are hard-deleted, with cascading integrity and absent-row idempotency.
- The bounded purge engine erases unrelated expired payloads through opportunistic seal cleanup.
- The manual purge command processes bounded batches and returns only an aggregate deletion count without identifiers.
- Wrong deployment tenant lookup indistinguishable from unknown token.
- Raw token absent from stored rows.
- Strict 32-byte token decoding, no weak fallback, golden SHA-256 vectors, and hostile token-length rejection.
- Stable canonical JSON fingerprint vectors match in TypeScript and Python.
- Exact stage field allowlists, per-field bounds, 64 KiB payload ceiling, unknown-field rejection, and no payload compression.
- The bounded display snapshot retains the accepted provider region and HTTPS launch URL as vendor display metadata while rejecting arbitrary provider payloads.
- Known payload upcast and unknown-future-version safe rejection.
- Real PostgreSQL tests for schema initialization and compare-and-swap row-count behavior, not only statement translation.
- Recovery storage contains the founder ballot before canonical submission, erases it during founder-command finalization, and contains no founder ballot during handoff or second pass.

### Decision gate

An independent critic must accept the store before route or UI integration proceeds.

## Slice R2: authenticated stateless transport

### Claim

Recovery requests reach the durable module without trusting browser-supplied ownership or leaking tokens and payloads through URLs, caches, or logs.

### Contract

The Next.js adapter verifies the signed session cookie, reads the server-only deployment tenant from `WATCHSIGNAL_HOUSEHOLD_ID`, and forwards through the existing backend service-token channel.

The deployment is explicitly single-tenant and does not claim that the current cookie contains household identity.

Seal, resume, and consume use request bodies and return `Cache-Control: no-store`.

R2 also implements the authenticated daily cleanup route and deployment schedule using the backend service token plus a dedicated cron secret.

### Boundary

Transport adapts authentication and JSON but does not implement recovery workflow decisions.

### Behavior

The route works after process restart and across two application instances sharing one database.

### Required evidence

- Fail-closed tests for absent household password, session secret, backend service token, or deployment household identifier.
- Handler-level signed-cookie verification tests that do not assume the outer proxy ran.
- No tenant identifier accepted or overridden from browser JSON, headers, queries, or cookies.
- No token in route path, query, history, or logs.
- Wrong deployment tenant and unknown-token parity.
- Shared-session household ownership enforcement.
- Hostile raw error suppression.
- No-store response checks.
- Strict same-origin/CSRF tests for JSON-only state-changing routes.
- Sensitive-log sentinel tests with injected token, household, session, profile, movie, title, ballot, and raw-error values.
- Multi-instance seal on one stateless web/API process and resume on another against PostgreSQL.
- The daily cleanup route fails closed unless both the backend service token and dedicated cron secret are valid.
- The daily schedule calls only that authenticated route, and route responses and logs contain only aggregate cleanup information without recovery identifiers.

### Decision gate

An independent critic must accept transport privacy before the process-local route is removed.

## Slice R3: canonical reconciliation and idempotency

### Claim

An interrupted founder ballot, handoff advance, or final ballot can be retried without duplicate writes, state regression, or misleading failure.

### Contract

Identical repeated session commands return canonical advanced state.

Conflicting repeats remain `409` conflicts.

Recovery stages advance through an explicit transition table, the ADR's durable command ledger, and its portable compare-and-swap algorithm.

Active work uses the ADR's expiring owner nonce, lease generation, same-command reclaim, and stale-owner fencing rules.

### Boundary

The shared-session module owns canonical session transitions.

The recovery module owns reconciliation and safe recovery projections.

Neither module owns the other module's persistence schema.

### Behavior

Recovery repairs crashes immediately before and after each canonical write.

The handoff projection never returns the first ballot.

The result projection is available only after both ballots are complete.

### Required evidence

- Two independent API processes and two database connections against real PostgreSQL.
- Lost founder-submit response followed by resume, including a forced kill after session commit and before recovery finalization.
- Forced kill after command claim and before canonical session write, followed by same-command reclaim after lease expiry.
- Lost handoff-advance response followed by resume at the same crash point.
- Lost final-submit response followed by resume at the same crash point.
- Identical replay returns success without another memory event.
- Changed replay returns conflict.
- Exact side-effect counts prove one durable reaction set and one deterministic taste-memory event under replay.
- Two concurrent resumes produce one canonical write and one command result.
- A late original worker cannot finalize after a reclaimed lease changes the owner nonce and generation.
- Abandoned in-progress command recovery is resolved through the ledger, expiring claim, and canonical state without stale-owner mutation.
- Shared-session command, conditional state transition, and deterministic taste-memory insertion share one database unit of work; exact replay produces one session mutation and one event per movie.
- Stage regression is rejected.
- Handoff and second-pass projection field allowlists exclude the earlier ballot.
- Final result reconstruction preserves canonical ordering, poster/backdrop, synopsis, cast, provider region, the provider HTTPS launch action, and deliberate missing-data fallbacks without storing an arbitrary shared-session or provider document.
- Solo and disconnected/local recovery behavior remains explicit.
- Solo and disconnected/local flows make no refresh-recovery claim, show current-tab guidance, clear private transient state after refresh, and return to safe setup without exposing an earlier ballot.

### Decision gate

An independent critic must accept functional, privacy, and concurrency behavior before browser integration proceeds.

## Slice R4: browser integration and cleanup

### Claim

The browser uses one deep recovery client and stores no sensitive transition state.

### Contract

The caller knows only `save`, `load`, and `clear`.

The checkpoint parser permits only version, opaque token, and expiry.

### Boundary

The recovery client owns browser storage and transport details.

The wizard owns screen navigation and accepted UI presentation.

### Behavior

Refresh at handoff, second-pass entry, matching pending, and matching failure restores the correct safe screen.

Back cannot reveal an earlier ballot.

The same recovery record advances through handoff, second-pass entry, final save, and matching.

Only acknowledged result mount, explicit reset, New night, or abandonment consumes it.

### Required evidence

- Browser storage contains no title, movie, candidate, reaction, ballot, score, session, household, or profile field.
- Reload during a slow founder save reaches a static safe handoff within the accepted animation budget.
- Reload after handoff advance reaches the clean second pass.
- Reload during final save reaches matching or an actionable failed state.
- Retry and local-result actions retain the final ballot.
- Reload immediately before and after every stage advance and consume boundary returns the correct safe state.
- Acknowledged result mount erases the payload; lost result response leaves it recoverable.
- Exact opener, focus containment, Escape, reduced motion, reduced transparency, and forced colors remain unchanged.
- 320, 390, and 430 widths, 390 by 568, and 200 percent equivalent reflow remain free of horizontal clipping.

### Decision gate

The builder cannot accept this slice.

A separate critic must run the real production flow and compare it against the accepted Transition reference.

### Completed outcome

R4 is independently accepted.

The browser checkpoint contains only version, opaque token, and expiry.

The deep browser client owns body-only recovery transport and session storage.

Production evidence covers handoff reload, second-pass reload, retained matching failure, local result, shared result, post-mount consume, and removal of the old query-token route.

The independent critic found no material R4 blocker.

## Slice R5: final release gate

### Claim

The complete WatchSignal journey survives the deployment failures the recovery feature promises to handle.

### Required evidence

- All web tests pass.
- All API tests pass.
- API compilation passes.
- TypeScript passes.
- The production build passes with the final tree.
- Hosted and beta preflight commands pass.
- A real 390 by 844 two-person journey completes through result, utilities, outcome, and restart.
- Two independent API processes and stateless web adapters against PostgreSQL resume a sealed handoff from the same database.
- The real Postgres schema migration and initialization pass under simultaneous startup.
- A simulated cold start during matching reaches result or actionable recovery without duplicate persistence.
- A deployed Vercel and Neon pilot trace creates recovery on one cold function invocation and resumes it after another invocation.
- Expired recovery returns a safe restart path.
- Daily cleanup and manual purge erase expired payloads, while access stops exactly at two hours.
- The actual Neon connection uses TLS and the deployment security configuration is recorded without claiming the database abstraction proves encryption.
- No diagnostic or sensitive recovery data appears in ordinary UI, browser storage, URLs, logs, or review-disabled network requests.
- Migration order, rollback to safe restart, and removal of the old query-token/process-local path are exercised.
- The worktree is reduced to an intentional reviewed release checkpoint before publication.

### Decision gate

S06 and S07 can be accepted only after their independent critic scores meet the Transition threshold with Functional fidelity at five.

S23 can be accepted only after the final integrated critic finds no remaining material gap.

The founder owns the release decision after those gates pass.

### Current outcome

All local R5 gates pass on the final tree.

The full web suite passes 252 of 252 tests.

The full API suite passes 418 tests with seven hosted-only tests skipped in the ordinary run.

The seven-test hosted PostgreSQL multi-process and crash-window suite passes.

API compilation, TypeScript, the 36-page production build, hosted preflight, beta preflight, tooling, MVP+4, MVP+5, and the live 390 by 844 dogfood journey pass.

The old process-local route is absent from the production manifest.

The local journey covers both private passes, durable handoff and matching, ranked result, evidence, watchlist, watched outcome, profile feedback, taste memory, recent-night history, and restart.

Two release actions remain outside local implementation.

The configured Vercel and Neon pilot must prove recovery across separate cold function invocations.

The founder must approve an intentional Git checkpoint and publication of the large redesign worktree.
