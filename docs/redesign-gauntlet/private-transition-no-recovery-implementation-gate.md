# Private-transition safe-restart implementation gate

This plan becomes active only if the founder accepts ADR-002 Option B.

It does not authorize the product or architecture decision on its own.

## Slice B1: establish safe interruption and abandonment

### Claim

An interrupted private transition returns to a clean, truthful setup state instead of depending on process-local recovery.

### Contract

Introduce a narrow server-issued abandonment capability and server contract before removing any currently deployed recovery path.

The capability is not a recovery checkpoint and cannot restore a stage, ballot, movie, candidate, result, or profile.

The server creates 32 random bytes when the canonical session is created, returns the unpadded base64url capability once, and stores only its SHA-256 digest bound to that session and deployment tenant in the same database transaction.

The browser stores one versioned private-transition-open envelope.

Its strict union is either `{version, kind: api, capability}` or `{version, kind: local}`.

The local variant records only that a private transition was open.

It contains no session, person, title, movie, reaction, ballot, candidate, result, profile, score, household, or stage.

Keep the accepted privacy seal, handoff, matching, Retry, and local-result behavior within the current open tab.

### Boundary

The wizard owns current-tab presentation and private in-memory state.

The shared-session service remains authoritative for already-submitted reactions.

The shared-session service also owns the capability binding and its lifecycle.

Neither browser history nor ordinary history may reveal an earlier private ballot.

### Behavior

API-backed couple sessions keep working normally while the tab remains open.

Solo and disconnected sessions keep their accepted current-tab flow.

On cold load or persisted back-forward-cache restoration, detection first copies a valid API capability into ephemeral memory, removes the reserved envelope key regardless of parse validity, clears transient private state, and installs `Session interrupted - start again.` without waiting for a network response or interaction.

Local and malformed envelopes require no network action.

Bounded best-effort abandonment may use only the captured in-memory API capability after the safe state is installed and cannot delay or reverse it.

### Required evidence

- Session creation atomically stores the digest of the server-issued 256-bit capability with the canonical session and deployment tenant.
- Only that exact capability may abandon its eligible incomplete session.
- The browser envelope contains no session ID, title, movie, reaction, ballot, candidate, result, profile, score, household, or stage.
- API-backed private transitions store the server-issued capability variant; solo and disconnected or local-only private transitions store the local variant.
- Completed result mount, explicit reset, and New night clear the envelope and any server binding.
- A stale capability cannot display an interruption after successful completion or mutate a completed session.
- Detection removes the reserved envelope key synchronously for valid API, valid local, malformed, and unknown-version values before any network work.
- Restart verifies the reserved key is absent before beginning a clean night.
- Failed abandonment delivery leaves the session hidden from ordinary history and eligible for the two-hour server maintenance path.
- Current-tab founder handoff, second pass, matching Retry, and local-result paths still pass.
- Reload at founder saving, handoff, second-pass entry, final saving, matching, and matching failure returns to the clean interruption state.
- Browser Back after reload cannot reopen either ballot.
- `pagehide` and `pageshow` with `event.persisted` invalidate private transition state before a back-forward-cache document can become interactive.
- Real traverse-away and Back tests at founder voting, handoff, second-pass voting, matching, and matching failure prove no title, reaction, or pressed state returns.
- Valid API or local envelopes, malformed content under the reserved envelope key, offline, timeout, `401`, `403`, `404`, `500`, and duplicate delivery all show the safe interruption state immediately and cannot restore private navigation.
- A second reload after malformed content, offline, timeout, `401`, `403`, `404`, `500`, duplicate delivery, or Restart does not show another interruption unless a new private transition writes a new envelope.
- Absence of the reserved envelope key on ordinary setup, mounted result, Taste Lab, household setup, credits, and other Utility reloads never shows the interruption state.
- Ordinary UI contains no claim that refresh recovery is available.
- Focus, reduced-motion behavior, and the accepted 650 ms privacy-seal bound remain unchanged.

### Decision gate

An independent critic must accept the safe interruption and abandonment foundation before the old recovery path is removed.

## Slice B2: remove the unreliable recovery implementation

### Claim

The product no longer depends on a process-local recovery payload or claims that private progress survives refresh.

### Contract

Remove the process-local recovery vault, opaque recovery checkpoint, startup restore path, and every public refresh-recovery claim only after B1 is accepted.

The B1 private-transition-open envelope remains because it cannot restore private progress.

Its API variant exists only to close the exact interrupted canonical session, while its local variant only selects the truthful interruption screen.

The authenticated server derives the deployment tenant and accepts an idempotent abandonment command only for that exact incomplete session.

### Boundary

The session service owns `abandoned_at`, capability-digest binding, and incomplete-session eligibility.

The browser owns presentation and delivery based on only the strict envelope.

History owns exclusion of incomplete or abandoned sessions.

### Behavior

Refresh captures a valid API capability into ephemeral memory, removes the envelope key regardless of validity, clears private state, and installs the safe restart screen synchronously, then attempts the captured capability with a short bounded timeout.

Missing delivery does not expose the session in ordinary history.

The authoritative inactivity timestamp is the canonical session's database-written `updated_at_ms`.

Founder submission, handoff advance, and final submission update it in the same session transaction.

A database-time maintenance query marks only `FOUNDER_REACTING`, `HANDOFF`, and `WIFE_REACTING` sessions abandoned when `updated_at_ms <= now_ms - 7_200_000`.

Reranked sessions and sessions with a saved outcome are never eligible.

The hosted authenticated daily maintenance call and bounded opportunistic cleanup on session creation use the same query.

If multiple incomplete sessions exist, the browser cannot select or abandon all of them broadly.

### Required evidence

- The process-local vault route and its `globalThis Map` are absent from the production route manifest.
- No recovery payload, stage, ballot, candidate, profile, result, session identifier, or recovery checkpoint remains in browser storage.
- No startup restore effect or token-in-query request remains.
- Strict envelope and abandonment-capability parser with an exact field allowlist.
- Signed-session and server-configured deployment-tenant enforcement.
- Caller-supplied household, session substitution, capability substitution, and cross-tenant attempts fail without revealing record existence.
- Exact bound capability abandons one eligible incomplete session once.
- Repeated abandonment with the same bound capability is a successful no-op.
- Reranked, completed-outcome, already-abandoned, and wrong-tenant sessions cannot be mutated through this path.
- More than one incomplete session does not create an ambiguous bulk action.
- A missing or undelivered capability leaves every incomplete session hidden from ordinary history.
- Maintenance proves just-before and exact two-hour boundary behavior using database time.
- Canonical private-session activity advances `updated_at_ms`; reads, browser retries, and failed abandonment do not.
- Process restart does not reset age, and the hosted daily plus opportunistic maintenance paths are executable-tested.
- The local envelope selects safe interruption without a server mutation and is cleared before restart.
- Malformed, unknown-version, and failed-delivery envelopes are consumed on detection and cannot create a repeating interruption loop.
- Normal result, reset, and New night clear the binding; a stale capability cannot abandon or display interruption for that completed session.
- Direct database assertions prove no reaction row is returned to the browser or ordinary history.

### Decision gate

An independent critic must accept removal, privacy, ownership, and history behavior before browser presentation is promoted.

## Slice B3: consumer recovery experience

### Claim

Losing a tab is disappointing but never confusing, technical, or privacy-compromising.

### Contract

One calm Utility state explains the interruption and offers one dominant restart action.

Copy must not mention APIs, servers, databases, sessions, tokens, recovery vaults, or implementation errors.

### Boundary

The interruption surface owns explanation and restart only.

It does not inspect, restore, summarize, or reveal the interrupted ballot.

### Behavior

Restart creates a new clean night using retained household setup, profiles, onboarding, defaults, and lasting taste memory.

Tonight-only reactions and unconfirmed transient intent are not restored.

### Required evidence

- Exact public copy and one dominant restart action.
- No movie, title, poster, reaction, person-specific ballot, or result appears on the interruption surface.
- Restart preserves durable household setup and memory but begins movie one with no pressed reaction.
- Keyboard focus begins on the interruption heading or restart action without a decorative focus artifact.
- Back cannot reveal the interrupted flow.
- Safe restart renders before abandonment delivery and remains visible across offline, timeout, rejected, and duplicate-delivery branches.
- Restart asserts the reserved key is absent before starting a clean night.
- Clean setup, mounted result, and ordinary Utility reloads without the reserved envelope key never render the interruption state.
- 320, 390, and 430 widths, 390 by 568, and 200 percent equivalent reflow remain unclipped.
- Reduced motion, reduced transparency, forced colors, 12 px text floor, and 44 px target floor pass.
- Source-masked independent comparison meets the Utility threshold.

### Decision gate

The builder cannot accept this slice.

A separate critic must run the real interruption and restart flow.

## Slice B4: final release gate

### Claim

WatchSignal ships an honest current-tab transition model without stale recovery infrastructure or private-history leakage.

### Required evidence

- All web tests pass.
- All API tests pass.
- API compilation passes.
- TypeScript passes.
- The production build passes with the final tree.
- Hosted and beta preflight commands pass.
- A complete real 390 by 844 two-person journey succeeds without refreshing.
- Reload at every private transition boundary reaches the safe interruption state and a fresh journey can start.
- Traverse-away and Back at every private transition boundary cannot revive a back-forward-cached ballot or pressed reaction.
- `pagehide` scrubs the cached document and preserves only the strict interruption envelope; `pageshow.persisted` repeats capture, envelope removal, and private-state scrubbing before the restored document becomes interactive.
- Current-tab Retry and local-result paths still work after induced persistence failure.
- Ordinary Recent nights excludes incomplete and abandoned sessions.
- The process-local route, recovery Map, checkpoint parser, startup restore code, and related production bundle strings are absent.
- The only permitted private-transition storage key is the strict versioned private-transition-open envelope; it contains either the opaque API abandonment capability or the fieldless local discriminator, never a canonical session ID or recovery state.
- The final production route manifest contains no private-transition vault endpoint.
- The worktree is reduced to one intentional reviewed release checkpoint before publication.

### Decision gate

S06 and S07 can be accepted only after their independent critic scores meet the Transition threshold with Functional fidelity at five.

S23 can be accepted only after the final integrated critic finds no remaining material gap.

The founder owns the release decision after those gates pass.
