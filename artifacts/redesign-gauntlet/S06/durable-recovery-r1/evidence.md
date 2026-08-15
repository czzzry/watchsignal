# Durable recovery R1 evidence

## Claim

A private-transition recovery record survives a fresh application module without storing a raw browser token or returning an earlier ballot to the next viewer.

## Contract

The public workflow interface is `seal`, `resume`, and `consume` over discriminated commands and stage-specific projections.

The browser token is 32 random bytes encoded as canonical unpadded base64url.

The database stores its SHA-256 digest, a versioned canonical payload, and a command ledger.

Access expires exactly two hours after the first seal and is never extended by a retry or read.

## Boundary

`PrivateTransitionRecovery` owns validation, versioning, idempotency, reconciliation, expiry, minimization, and safe projections.

`SQLitePrivateTransitionRecoveryStore` owns portable SQL row changes and cascading deletion.

Recommendation ranking, session transitions, browser navigation, and presentation remain outside R1.

## Behavior proved in quiet mode

- A fresh module and database connection resume a founder seal as a ballot-free handoff projection.
- Identical command replay returns the original handle without extending expiry.
- Same token with a different command or ballot conflicts without replacing stored recovery.
- Two simultaneous identical seals create one recovery row and one command row.
- A lost second-pass persistence response reconciles from the command ledger.
- Canonical founder submission rewrites recovery storage without the founder ballot.
- Second-pass storage and projection contain the display snapshot but no founder ballot.
- Final sealing stores only the unsent final ballot.
- Canonical rerank rewrites recovery storage without either ballot and returns canonical result order.
- Consume is idempotent and hard-deletes recovery plus command rows through cascade.
- Exact expiry, bounded opportunistic cleanup, manual purge batches, cross-tenant denial, strict fields, size limits, version handling, and token canonicality are executable-tested.
- All seal commands reject non-text identifiers, and both ballot variants reject untyped ballot or display entries before any persistence work.
- The browser converter bounds live synopsis, cast, provider, access, provider region, provider HTTPS launch URL, tone, and structured-evidence text to the server schema on whole Unicode code points; oversized artwork URLs become the deliberate missing-art fallback.
- Provider region and the HTTPS launch URL are narrowly allowlisted vendor display metadata required for result reconstruction and the accepted provider action, not an arbitrary provider payload.
- Python and TypeScript produce the same canonical founder-command SHA-256 fingerprint.

The current canonical-state reconciliation tracers exercise provisional single-process storage behavior only.

They do not satisfy R3 lease ownership, crash-window recovery, canonical side-effect exactness, stale-owner fencing, or multi-process PostgreSQL gates.

## Validation

- Focused API recovery and maintenance suites: 31 passing in total.
- The opt-in real PostgreSQL portability and concurrency test passes against the configured hosted database in 12.936 seconds, and its recovery-only rows are cleaned in the test's `finally` boundary.
- Manual purge command returned the aggregate-only payload `{"deleted":0}` against an isolated temporary database; the temporary database was then removed.
- Focused TypeScript command suite: 8 passing.
- Full web suite: 235 passing.
- Full API suite: 386 passing and one opt-in real-PostgreSQL test skipped, 387 tests in total.
- PostgreSQL adapter initialization, shared-store concurrency, and compare-and-swap behavior pass through two independent store instances against the configured hosted database.
- API compilation passes.
- The current production web build passes TypeScript and generates all 33 static pages successfully.

R1 proves the bounded purge engine and manual aggregate-only purge command.

No authenticated daily cleanup route or schedule is claimed in R1.

R2 must implement and prove that route and schedule using the backend service token plus a dedicated cron secret.

## Decision

The independent standards review accepts the revised R1 implementation.

The independent spec review found no remaining static defect before the PostgreSQL run.

The final independent rejudge accepts R1 after the hosted PostgreSQL test proved two-store initialization, one-winner compare-and-swap behavior, and cleanup.

R1 is promoted.

Authenticated transport integration may begin under the separate R2 gate.

This R1 evidence does not claim browser automation.
