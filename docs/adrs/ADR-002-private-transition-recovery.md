# ADR-002 Durable private-transition recovery

## Status

Accepted on 2026-08-13 by the founder.

Option A is selected for implementation in quiet mode.

Option B remains the documented rollback path if durable recovery cannot pass its privacy, concurrency, deployment, or usability gates.

The corresponding implementation gates are:

- Option A: `docs/redesign-gauntlet/private-transition-recovery-implementation-gate.md`
- Option B: `docs/redesign-gauntlet/private-transition-no-recovery-implementation-gate.md`

## Context

WatchSignal has accepted mobile experiences for sealing the first private ballot, handing the phone to the next person, saving the final ballot, matching, retrying a failed match, and showing a local result.

The accepted product experience promises that those private transition states can survive a page refresh.

Before this decision was implemented, the browser stored an opaque checkpoint plus non-ballot stage metadata while the corresponding recovery payload lived in a process-local JavaScript `Map` in the Next.js process.

That `Map` works in a single long-lived local process but is lost on a restart, deployment, or cold start and is not shared between Vercel instances.

ADR-001 already selects Vercel for the web and FastAPI applications and Neon PostgreSQL through the existing `DATABASE_URL` seam for hosted persistence.

That process-local recovery implementation could not truthfully support its refresh-recovery promise in the accepted hosted architecture.

The recovery data can include an unsent private ballot, five candidate display records, session and participant identifiers, and enough state to resume the private transition.

This is sensitive transient household data even though the same database already stores submitted session reactions.

The decision must preserve pass-the-phone privacy, survive multi-instance routing and cold starts, remain inspectable locally through SQLite, add no new vendor, and leave recommendation scoring and ordering unchanged.

## Proposed decision

Choose Option A and replace the process-local vault with one durable `PrivateTransitionRecovery` module backed by the existing SQLite and PostgreSQL database seam.

The module has a small workflow interface:

```text
seal(deployment_tenant, token, command) -> recovery handle
resume(deployment_tenant, token) -> safe stage projection
consume(deployment_tenant, token) -> nothing
```

The web caller is thinner:

```text
recovery.save(command) -> checkpoint
recovery.load() -> safe stage projection or null
recovery.clear() -> nothing
```

The caller does not manage token hashing, deployment tenancy, schema versions, expiry, command revisions, or reconciliation.

`command` is a discriminated union rather than an arbitrary snapshot or stage write.

```text
SealCommand =
- SealFounderBallot(command_id, canonical_session_id, ballot, display_snapshot)
- OpenSecondPass(command_id, optional canonical_session_id)
- SealFinalBallot(command_id, optional canonical_session_id, ballot, display_snapshot)
- UseLocalResult(command_id)
```

The founder seal binds the recovery to the canonical session.

Later commands normally omit that identifier and derive it from the token-owned recovery record, while the optional identifier remains a compatibility check when supplied.

The module derives stage, actor, participants, workflow and payload versions, revision, expiry, and reconciliation behavior from the command and canonical session.

`resume` returns a strict stage projection.

```text
ResumeProjection =
- HandoffPending(recipient_label, can_begin=false)
- HandoffReady(recipient_label, can_begin=true)
- SecondPassReady(display_snapshot)
- MatchingPending()
- MatchingFailed(can_retry=true, can_use_local=true)
- ResultReady(canonical_session_id, result_source, final_reactions, display_snapshot)
```

Handoff projections contain no ballot or movie field.

The second-pass projection contains display metadata for the active shortlist but never the first ballot.

Matching projections do not return either ballot.

The result projection is released only after the private transition is complete.

It contains the canonical session reference, shared-or-local result source, the final participant's five public reaction values, and the bounded five-title display snapshot needed to mount the accepted result.

It contains no founder ballot, scorer payload, profile evidence, or arbitrary provider response.

The browser generates a 256-bit random token and stores only an opaque checkpoint in `sessionStorage`.

The browser never stores titles, candidates, reactions, scores, ballot data, or profile identifiers in that checkpoint.

The raw token is sent only in an authenticated request body, never in a URL, query string, application log, or database row.

The database stores a SHA-256 digest of the token.

The Next.js route remains an authenticated, stateless forwarding adapter.

The current signed cookie proves only that the caller passed the one deployment's household passphrase.

It does not contain a household identifier and must not be described as a household identity claim.

For the accepted single-household pilot, the adapter uses a server-only `WATCHSIGNAL_HOUSEHOLD_ID` configuration value as the deployment tenant.

The route fails closed unless the household passphrase, session secret, backend service token, and deployment household identifier are all configured.

The browser cannot supply or override the deployment tenant through JSON, headers, query strings, or cookies.

Route handlers verify the signed session cookie even when the outer proxy already ran.

Adding another household requires a new signed household claim or account decision before this module can claim cross-household authorization.

The FastAPI module verifies both recovery-record ownership and shared-session household ownership.

Unknown, expired, consumed, and wrong-household records return the same public not-found result.

The record uses a strict versioned schema and rejects unknown fields, invalid stages, inconsistent participants, invalid reaction values, candidate/reaction mismatches, and oversized payloads.

The fixed access expiry remains two hours from initial creation and is not extended by retries or reads.

The record remains recoverable through handoff, the deliberate Begin action, the second private pass, and matching.

It is not consumed merely because the server reached `HANDOFF`, `WIFE_REACTING`, or `RERANKED`, because the response may have been lost before the browser installed the safe next state.

The browser consumes it only after acknowledging that the result projection is mounted, or after explicit reset, New night, or abandonment.

Consume hard-deletes the command-ledger rows and recovery row in one transaction through a cascading foreign key.

An absent row is treated as a successful repeated consume, so idempotency does not require retaining household, session, stage, actor, command, or fingerprint data.

Expired records are inaccessible immediately at the two-hour boundary.

Every `seal` first deletes a bounded batch of expired payloads.

R1 proves the bounded purge engine through opportunistic seal cleanup and a manual aggregate-only purge command.

R1 does not implement or claim the hosted daily cleanup route or schedule.

R2 installs the authenticated daily cleanup route and schedule because Vercel Hobby cannot run cron more frequently than once per day and does not guarantee an exact invocation minute.

The product therefore promises two-hour access expiry, not physical deletion at exactly two hours.

Physical payload erasure is guaranteed on consume and no later than the successful daily cleanup following expiry under the selected pilot plan.

The R2 cleanup route is idempotent, uses the backend service token plus a dedicated cron secret, and emits no record identifiers.

The R1 manual purge command remains available for missed runs or incident response and reports only an aggregate deletion count.

The module reconciles its record against the canonical shared-session state after any interrupted request.

If an identical founder or partner ballot already advanced the shared session, the repeated operation returns the canonical session as success.

If the repeated ballot differs, the operation remains a conflict.

The same rule applies to an interrupted handoff advance.

Founder submission, handoff advance, and final submission remain owned only by the shared-session module.

The recovery module coordinates commands and projects outcomes but never reimplements canonical session transitions.

Every recovery operation has a 256-bit command ID, command kind, canonical request fingerprint, and starting recovery revision.

A durable command ledger records recovery ID, command ID, command kind, request fingerprint, result revision, and status.

The same command ID and fingerprint returns the recorded result.

The same command ID with a different fingerprint is a conflict.

A new command at the next recovery revision is allowed only by the explicit workflow transition table.

Concurrent workers acquire a command with one portable compare-and-swap statement that updates the expected revision only when no active command exists and the record has not expired.

Exactly one affected row owns the command.

The claim stores a random 256-bit lease-owner nonce, an incremented lease generation, and a 30-second lease expiry computed from UTC epoch milliseconds read inside the database transaction.

The database adapter owns the SQLite and PostgreSQL clock query while the workflow remains independent of database-specific time syntax.

A worker may renew only by compare-and-swap on recovery ID, command ID, owner nonce, lease generation, starting revision, and an unexpired recovery record.

If a worker dies before the canonical write, `resume` may reclaim only the same command ID, kind, and request fingerprint after the lease expires.

Reclaim compares the existing expired claim, installs a new owner nonce, increments the lease generation, and leaves the workflow revision unchanged until finalization.

A different command cannot take over an unfinished command.

Finalization matches the command ID, current owner nonce, lease generation, and starting workflow revision.

A late original worker therefore cannot finalize or mutate a later stage after takeover.

Zero affected rows triggers command-ledger lookup and canonical-state reconciliation rather than a blind retry.

This avoids dialect-specific row locks and `RETURNING` behavior in the module interface.

If a worker dies after the canonical session write but before finalizing the recovery command, a later `resume` compares the stored command fingerprint with canonical shared-session state and finalizes that command without resubmitting it.

The shared-session interface accepts the same durable command ID for founder submission, handoff advance, and final submission.

It makes identical repeats return canonical state while conflicting repeats remain `409`.

The shared-session module persists its own command ledger in the same database as the session and taste-memory events.

One shared-session unit-of-work transaction records the command fingerprint, applies the conditional session transition, and inserts the deterministic taste-memory events.

An exact repeated command reads that durable result and performs no second session or taste-memory mutation.

The implementation replaces the current ordering that writes memory events before saving the session.

Session persistence and recovery-command completion use separate transactions, so correctness relies on canonical-state reconciliation after the crash window rather than pretending they are one distributed transaction.

Taste-memory writes triggered by session reactions use deterministic event IDs and are asserted exactly once under identical replay.

When canonical founder submission is confirmed, recovery finalization rewrites `payload_json` in the same recovery transaction to erase the founder ballot.

Handoff and second-pass storage then contains only the bounded display snapshot and canonical session reference.

If recovery resumes after the canonical write but before that rewrite, canonical-state reconciliation performs the same ballot erasure before returning a handoff projection.

Stage-specific projections prevent the first ballot from being returned while the second person is at the handoff or private-reaction screen.

The module returns the minimum data required for the active stage rather than returning its stored document wholesale.

No recommendation weight, Match Index behavior, candidate order, session mode, reaction meaning, visual direction, or result action changes under this decision.

## Data model

The initial portable table should contain:

```text
private_transition_recoveries
- recovery_id primary key
- token_hash unique lowercase 64-character hex
- household_id
- shared_session_id nullable
- workflow_version integer
- payload_version integer
- stage allowlisted text
- actor allowlisted text
- revision integer
- payload_json canonical UTF-8 text nullable
- payload_fingerprint lowercase 64-character hex nullable
- active_command_id nullable
- active_command_kind nullable
- active_command_request_fingerprint nullable lowercase 64-character hex
- lease_owner_nonce nullable lowercase 64-character hex
- lease_generation integer
- lease_expires_at_ms integer nullable
- expires_at_ms integer
- consumed_at_ms integer nullable
- created_at_ms integer
- updated_at_ms integer

private_transition_recovery_commands
- recovery_id
- command_id lowercase 64-character hex
- command_kind allowlisted text
- request_fingerprint lowercase 64-character hex nullable after consume
- starting_revision integer
- result_revision integer nullable
- status allowlisted text
- created_at_ms integer
- updated_at_ms integer
- primary key on recovery_id and command_id
```

The command table has a foreign key to the recovery row with `ON DELETE CASCADE`.

The recovery table has an index on household and expiry.

All instants use UTC epoch milliseconds stored as SQLite `INTEGER` and PostgreSQL `BIGINT`.

Payload JSON is canonical UTF-8 `TEXT`, not a dialect-specific JSON type.

Initial acquisition and expired-lease reclaim each use one `UPDATE ... WHERE revision = ?` statement with the exact active-command and lease predicates defined above and verify affected row count in both adapters.

The design does not depend on `SELECT FOR UPDATE`, `RETURNING`, database-native JSON, or database-local clock syntax.

The payload stores only the fields required to reconstruct the supported private stage.

Submitted shared-session state remains canonical and is not duplicated as an arbitrary `SharedSessionPayload` blob.

Candidate display metadata may be retained because the shared-session table does not contain everything required to rebuild the accepted private and result surfaces after a refresh.

The display snapshot allowlist is limited to source movie ID, title, year, runtime label, poster and backdrop HTTPS URLs, synopsis, up to five genres, up to three cast names and roles with HTTPS profile URLs, bounded provider names, access labels, provider region, and provider HTTPS launch URL, language-access copy, tone label, and the existing structured evidence identifiers required by public copy.

Provider region and the HTTPS launch URL are allowlisted vendor display metadata required to reconstruct availability and preserve the accepted provider action semantics.

They are not permission to retain an arbitrary or raw provider payload.

It excludes raw debug history, scorer internals, free-form raw error detail, cookies, profile memory, unrelated prior batches, arbitrary provider payloads, and duplicate shared-session documents.

Every string and array has a field-specific length or count limit.

The complete UTF-8 encoded payload must not exceed 64 KiB and is never compressed.

Stage-specific stored schemas are:

- Founder seal: active five-title display snapshot plus only the unsent founder ballot.
- Handoff and second-pass: display snapshot and canonical session reference only; the submitted founder ballot has been erased from recovery storage.
- Final seal and matching failure: display snapshot plus only the unsent final ballot; already-submitted founder data comes from the canonical session.
- Result-ready: display snapshot only; canonical rerank and reactions come from the session.

`UseLocalResult` returns the final reactions directly for the current authenticated response without advancing the durable record to result-ready.
Until the browser acknowledges and consumes that response, the record remains final-sealed or matching-failed, where retention of the unsent final ballot is already allowed.
If the response is lost, the household returns to the safe matching recovery choices instead of leaving a ballot inside a result-ready payload.

Durable refresh recovery under Option A applies only while the recovery service and a canonical shared couple session are reachable.

Solo mode and a disconnected or local-only couple round remain available in the current tab, but do not claim refresh recovery under this decision.

Those paths show `Keep this tab open while we finish.` during the transition and use a privacy-safe interruption marker containing no title, ballot, movie, profile, or session identifier.

After a refresh they clear transient private state and return to setup with `Session interrupted - start again.`

This narrower promise is deliberate because the local scorer has no canonical server operation against which recovery can reconcile without returning a private ballot or moving recommendation ownership into the recovery module.

The versioned parser upcasts known older payload versions and rejects an unknown future version with a safe incompatible result.

Canonical command fingerprints are SHA-256 lowercase hexadecimal over a stable-key, recursively canonical JSON encoding of the validated command, including command kind, workflow version, payload version, and canonical session reference.

The implementation publishes golden canonicalization vectors so TypeScript and Python compute identical fingerprints.

## Threat model and controls

### Token disclosure

The raw token could otherwise leak through access logs, browser history, query strings, or database inspection.

The browser creates the token with `crypto.getRandomValues(new Uint8Array(32))`, encodes it as unpadded base64url, and has no UUID or weak-randomness fallback.

The server rejects any token that does not decode to exactly 32 bytes before hashing it with SHA-256 to lowercase hexadecimal.

The control is that token construction, `sessionStorage` only, request-body transport, database hashing, `Cache-Control: no-store`, and a ban on token logging.

### Cross-tenant access

A caller could otherwise present another household's token.

The control is the server-configured deployment tenant, lookup by both tenant and token digest, shared-session household ownership verification, and indistinguishable not-found responses.

The accepted shared-passphrase pilot is one configured deployment tenant and does not claim household identity or per-person authentication.

True multi-household support requires a later signed household claim or account decision and is not silently introduced here.

### Replay and lost responses

A request can commit and lose its response, causing a later retry after the session state already advanced.

The control is canonical-state reconciliation, exact request fingerprints, idempotent identical repeats, conflicts for changed repeats, the durable command ledger, and the explicit compare-and-swap algorithm.

### Concurrent workers

Two Vercel instances can attempt the same resume operation.

The control is shared PostgreSQL state plus the concrete compare-and-swap and command-ledger algorithm inside database transactions.

### Excess retention

Private state could otherwise remain after the household no longer needs it.

The control is fixed two-hour access expiry, no retry-based extension, payload erasure on acknowledgement-driven consume, bounded cleanup on every seal, the R1 manual aggregate-only purge command, and the R2 authenticated daily cleanup route and schedule.

### Sensitive observability

Structured logs could otherwise reveal tokens, identities, movies, or ballots.

The control is allowlisted telemetry containing only operation, stage, outcome, schema version, revision change, latency, age bucket, and payload-size bucket.

Logs must never contain raw or hashed tokens, household IDs, session IDs, profile IDs, movie IDs, titles, candidates, reactions, payload bodies, cookies, or raw exceptions.

### Database access

An operator or attacker with database access can inspect transient payloads.

The initial control is the existing restricted application credential, hosted database encryption at rest and in transit, strict retention, and access limited to the existing database trust boundary.

Neon documents AES-256 encryption at rest and TLS-encrypted connections, but deployment validation must verify the actual connection configuration instead of treating the database abstraction as proof.

Application-level field encryption would require a key-storage, rotation, recovery, and incident-response decision and is not being implied by this ADR.

### Cross-site request submission

A malicious origin could otherwise attempt a state-changing recovery request through the signed-in browser.

The controls are an HTTP-only secure `SameSite=Lax` cookie, handler-level session verification, JSON-only POST and DELETE requests, and a non-simple `X-WatchSignal-Recovery` application header that a cross-origin browser cannot send without a CORS preflight that the route never permits.

Exact same-origin `Origin`, `Sec-Fetch-Site`, or `Referer` checks remain supported as browser and proxy fallbacks.

CSRF tests cover missing, foreign, same-origin, and application-marker requests without weakening non-browser server adapters.

Local SQLite security continues to depend on host filesystem access controls.

## Options considered

### Option A: durable recovery in the existing database

This preserves the accepted refresh-recovery experience across restarts, deployments, cold starts, and multi-instance routing.

It uses infrastructure already selected in ADR-001 and keeps local SQLite parity.

It temporarily retains an unsent private ballot server-side for at most two hours.

It requires schema, reconciliation, idempotency, expiry, and privacy tests.

This is the recommended option.

### Option B: remove refresh recovery

This deletes the process-local vault, recovery payload, browser checkpoint, and startup restore path.

Private progress remains only in the open tab until submitted to the existing shared session.

A refresh during handoff or matching returns to a clean setup state with concise copy such as `Session interrupted - start again.`

Option B adds an explicit `abandoned_at` marker to an interrupted shared session or deletes a local-only session.

Ordinary Recent nights and result-history routes exclude any session that is not reranked and not associated with a saved outcome.

When an API-backed session is created, the server returns a 256-bit opaque abandonment capability and stores only its SHA-256 digest bound to that canonical session and deployment tenant in the same database transaction.

The browser stores one strict versioned private-transition-open envelope.

Its API-backed variant contains only version, `kind: api`, and that capability.

Its solo or disconnected/local-only variant contains only version and `kind: local`.

Neither variant contains a caller-selected session identifier, stage, person, title, movie, reaction, ballot, candidate, result, profile, score, or household field.

On cold load or persisted back-forward-cache restoration, the app copies a valid API capability into ephemeral memory, removes the reserved envelope key regardless of parse validity, synchronously clears all private React state, and installs `Session interrupted - start again.` before attempting bounded best-effort abandonment.

Offline, timeout, rejected, missing, malformed, and duplicate delivery cannot delay or reverse the safe restart state.

Local and malformed envelopes require no network action.

A valid API capability may be delivered only from ephemeral memory after storage has been scrubbed.

Restart verifies the reserved key is absent before beginning a clean night.

A second reload cannot repeat the interruption unless a new private transition wrote a new envelope.

Presence of the reserved envelope key, including malformed content, selects the safe interruption state before parsing or network work.

Absence of that key on clean setup, mounted result, and ordinary Utility reloads preserves the ordinary screen and never invents an interruption.

The server derives the deployment tenant, resolves the bound session from the capability digest, and may abandon only that session in an incomplete private-transition state.

If the capability is missing because the tab was evicted or closed, a maintenance rule uses database time to mark only founder-reacting, handoff, or partner-reacting sessions abandoned when their canonical `updated_at_ms` reaches two hours of inactivity.

Canonical private-session writes advance that timestamp; reads and retries do not.

Reranked sessions and sessions with a saved outcome are never eligible.

Ordinary history excludes incomplete sessions immediately regardless of whether the abandonment marker was delivered.

If more than one incomplete session exists, no broad browser request may choose among them or abandon all of them.

Only the exact capability can abandon immediately, and remaining sessions age out through bounded opportunistic cleanup plus the hosted maintenance rule.

Back and history tests prove that submitted first-ballot data cannot be reopened through ordinary UI even though it remains in the canonical shared-session record for integrity and audit.

This option has the smallest retention and implementation surface.

It intentionally gives up seamless recovery on mobile browsers, where refreshes, tab eviction, and app restarts are realistic.

### Option C: keep the process-local vault

This requires the least immediate work.

It contradicts the accepted Vercel deployment because recovery depends on which warm process handles each request.

This option is rejected for release.

### Option D: add Redis or another recovery store

This provides shared expiry-aware storage but introduces a second hosted persistence tier, vendor, configuration path, and operational failure mode.

The existing PostgreSQL seam already supplies the required durability and concurrency primitives.

This option is rejected for the pilot.

## Tradeoffs

Option A adds a bounded database table and one workflow-aware module but concentrates privacy, expiry, concurrency, retry, and compatibility rules behind one interface.

Option B is simpler and retains less transient data but weakens a polished mobile flow at exactly the points where users may refresh or lose a tab.

Option A makes the database trust boundary slightly larger because it temporarily includes unsent ballots.

Option A avoids a new vendor and is compatible with the existing local and hosted storage adapters.

Option A requires exact duplicate reconciliation in the shared-session module, which also improves behavior after lost responses outside recovery.

Vercel Hobby permits a cron job only once per day and does not promise exact invocation within the selected hour, so this design distinguishes immediate logical access expiry from later physical cleanup.

If the founder requires physical deletion within two hours even when the household is inactive, Option A additionally requires a paid or external scheduler decision and ADR-001 must be revisited.

## Reversibility

Medium.

The recovery table and routes can be removed later without changing recommendation data or ranking logic.

The browser checkpoint format remains versioned so old checkpoints can fail safely after a rollback.

Choosing Option B later requires deleting outstanding recovery rows and changing public copy, but does not require migrating durable recommendation history.

Deployment order is database schema, FastAPI recovery module, stateless Next.js adapter, then the browser client.

The process-local route remains disabled once the durable adapter is active and is never restored by rollback.

A rollback either keeps the compatible durable route or falls back to Option B's safe restart behavior.

Unknown future checkpoints fail safely, outstanding rows remain purgeable through the maintenance command, and old query-token checkpoints are never re-enabled.

## Revisit triggers

- The pilot expands beyond one configured deployment tenant.
- Recovery records approach the selected database plan's storage or throughput limits.
- The two-hour retention window proves too short or unnecessarily long in real use.
- Security policy requires application-level encryption for transient ballots.
- The product adds simultaneous multi-device voting.
- The recovery workflow expands beyond private handoff and matching.
- Hosted cold starts or database wake-up latency make recovery visibly slow.

## Consequences

Option A is implemented without changing the accepted S06 and S07 visual direction.

Durable restart, multi-instance, privacy, idempotency, expiry, browser integration, and the complete local mobile journey pass independent review.

The production BFF becomes stateless for recovery.

The current process-local `Map` and token-in-query behavior are removed.

The current single-household authentication model remains unchanged and must not be described as multi-household authorization.

No new paid vendor or infrastructure service is introduced.

The hosted acceptance run uses two independent FastAPI processes and stateless web adapters against PostgreSQL.

The configured Vercel and Neon pilot must still repeat the critical cold-start path before publication.

## Sources

- ADR-001 Hosted Android Pilot.
- The accepted S06 and S07 transition designs and their independent architecture audits.
- The current process-local recovery route and browser checkpoint contracts.
- The existing SQLite/PostgreSQL storage seam and shared-session state machine.
- The complete 390 by 844 post-seal production journey from 2026-08-13.
- Vercel Cron Jobs usage and pricing documentation, which limits Hobby schedules to once per day and notes imprecise invocation timing.
- Neon security documentation for encryption at rest and encrypted connections.
