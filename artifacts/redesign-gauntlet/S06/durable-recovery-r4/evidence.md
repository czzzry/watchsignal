# Durable private-transition recovery R4 evidence

## Claim

An API-backed couple can refresh during the private handoff, second pass, or matching transition without exposing the first ballot or losing the final ballot.

## Contract

The browser checkpoint contains exactly `version`, a 256-bit opaque recovery token, and `expiresAt`.

Every durable command and projection is a strict discriminated union.

The result is consumed only after the safe result state is mounted, or after an explicit reset or New night.

## Boundary

The browser recovery client owns token creation, session storage, and authenticated body-only requests.

The FastAPI recovery module owns workflow order, persistence, expiry, safe projections, reconciliation, and consume.

The shared-session service remains the only owner of founder save, handoff advance, final save, and taste-memory side effects.

Recommendation scoring, ordering, provider behavior, and the accepted transition visuals are unchanged.

## Production behavior

A clean production run at 390 by 844 sealed the founder ballot, showed the privacy-safe handoff, and restored the same handoff after reload.

Beginning the next pass advanced the durable record and a reload restored the second person's first card without revealing the founder ballot.

An induced recovery transport failure after the fifth final reaction retained that reaction and showed both Try again and Show local result.

Show local result mounted the five-title result, consumed the durable record, removed the checkpoint, and left the canonical shared session in its pre-rerank state.

A second clean run reached the shared ranked result, consumed the durable record, removed the checkpoint, and persisted exactly five reactions for each participant.

The old process-local `/api/private-transition-vault` route and its query-token path are absent from the final production route manifest.

## Browser artifacts

- `handoff-before-reload-390x844.png`
- `second-pass-after-reload-390x844.png`
- `matching-failed-retained-390x844.png`
- `local-result-after-failure-390x844.png`
- `shared-result-390x844.png`

Every image is exactly 390 by 844 pixels.

## Executable evidence

- Focused browser and transport contracts: 30 of 30 passed.
- Focused API recovery, route, and maintenance contracts: 52 of 52 passed.
- Hosted PostgreSQL multi-process and crash-window suite: 7 of 7 passed in 287.454 seconds.
- Full web suite: 252 of 252 passed.
- Full API suite: 418 tests passed with 7 hosted-only tests skipped in the ordinary run.
- API compilation passed.
- TypeScript passed after removing stale generated route metadata.
- The final production build passed and generated 36 pages without the removed vault route.
- Hosted preflight, beta preflight, and tooling tests passed.
- `git diff --check` passed.

## Evidence limits

The hosted multi-process proof uses the configured PostgreSQL database and fresh local API processes rather than deployed Vercel function invocations.

The beta preflight warns that the ordinary local environment uses its default API address and demo recommendation source unless the live dogfood variables are supplied.

The large redesign worktree remains uncommitted and must become an intentional local checkpoint before publication.

## Decision

R4 is independently accepted.

The independent critic found no material blocker in checkpoint privacy, safe restore plans, retained matching recovery, post-mount consume, stateless routes, or old-vault removal.

S06 earned ACCEPT at 37 of 40 with Functional fidelity at 5 of 5.

S07 earned ACCEPT at 36 of 40 with Functional fidelity at 5 of 5.

R5 local release evidence passes, but publication remains founder-owned.
