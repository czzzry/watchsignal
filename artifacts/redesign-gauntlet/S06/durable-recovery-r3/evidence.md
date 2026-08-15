# Durable recovery R3 evidence

## Claim

An interrupted founder ballot, handoff advance, or final ballot can be retried without duplicate canonical writes, duplicate taste-memory events, state regression, or stale-worker finalization.

## Contract

Shared-session commands use a caller-supplied 64-character command identifier and a canonical request fingerprint.

An exact replay returns the canonical advanced session, while the same command identifier with a different request is a conflict.

Recovery work uses a database-time 30-second lease with a 256-bit owner nonce, an incrementing generation, the starting recovery revision, the exact command kind, and the exact request fingerprint.

Only the same command and fingerprint may reclaim an expired lease.

Every finalizer verifies the command, fingerprint, starting revision, owner nonce, generation, and unexpired database lease.

## Boundary

`SharedSessionService` owns founder submission, handoff advance, final submission, canonical state transitions, and deterministic taste-memory events.

`PrivateTransitionRecovery` owns command claims, crash reconciliation, ballot minimization, recovery-stage advancement, and safe projections.

The shared-session transition, shared-session command result, and taste-memory insertion share one database transaction.

The recovery transaction remains separate and reconciles against canonical session state after a crash window.

## Behavior proved

- Concurrent founder resumes invoke one canonical writer while the other caller receives a safe pending projection.
- A worker terminated after command claim but before the founder write is reclaimed after database-time lease expiry.
- A worker terminated after the founder write but before recovery finalization is reconciled without a second side effect.
- Handoff advance is recovered both before its canonical write and after its canonical commit.
- Final submission is recovered both before its canonical write and after its canonical commit.
- A late original worker cannot finalize after another worker reclaims the lease.
- A different command cannot take over an expired claim, and its speculative ledger row is removed.
- Founder and final ballots are removed from the recovery payload after canonical finalization.
- Exact founder, handoff, and final command replay returns canonical state.
- Reusing a command identifier with different content returns a conflict.
- An injected taste-memory failure rolls back session state, the command ledger, and memory together.
- Consume continues to hard-delete the recovery record and its command rows through the cascading foreign key.

## Validation

- Focused recovery and session API suites passed 64 tests before the final lease-specific tracer was added.
- The complete local private-transition recovery suite passed 38 tests before the final lease-specific tracer was added.
- The final lease-specific same-command reclaim and stale-owner test passed independently.
- The hosted PostgreSQL recovery suite passed all 7 tests in one 230.669-second run.
- The hosted suite used fresh spawned API processes, real process termination at each crash window, two database connections, and direct exact-side-effect assertions.
- The full API suite completed 413 tests with 406 passing and 7 opt-in hosted PostgreSQL tests skipped.
- The full web state suite passed 247 tests.
- API compilation passed.
- TypeScript passed.
- The generated TypeScript API contract was regenerated and its export tests passed.
- Scoped diff validation passed.
- No browser, preview server, watcher, or build process was left running.

## Decision

The independent critic found no material functional, privacy, concurrency, PostgreSQL-portability, or retention blocker and accepted R3.

R3 is promoted.

R4 now owns the deep browser client, the strict token-only checkpoint, safe stage restoration, result acknowledgement, and removal of the process-local vault after independent browser acceptance.

This evidence does not claim R4 browser integration, old-vault removal, a final production build, or deployed Vercel cold-start proof.
