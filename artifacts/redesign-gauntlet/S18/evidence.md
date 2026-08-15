# S18 Taste Lab evidence

## Claim

One person can teach WatchSignal one movie at a time without encountering a research dashboard.

## Contract

The five existing API labels remain exact.
`havent_seen` remains familiarity-only.
A selected decision stays attached to its profile and movie until a remote save succeeds or the person explicitly keeps it locally.

## Boundary

The Taste Lab page owns presentation, one-active-movie navigation, and honest local recovery.
Existing queue, profile, rating, storage, and API semantics remain unchanged.

## Behavior

The first viewport presents profile identity, batch progress, one real poster, four preference choices, a separate familiarity choice, and one Save and next action.
Queue provenance and progress analytics are moved behind a secondary summary.
Loading, empty, exhausted, saving, failed, built-in local, and local-exhausted states use household language.

## Evidence

Focused S18 contract tests passed 5 of 5.
The full web state suite passed 176 of 176.
The focused Taste Lab API suite ran 17 passing tests without a reported failure.
TypeScript and diff checks passed.
The production build reached the optimized-build compile stage but remained active during handoff and is unproven.

Real browser click-through at 390 by 844 selected a familiarity-only answer, confirmed `aria-pressed`, saved it, and advanced from `Austin Powers: The Spy Who Shagged Me` to `The Matrix` with `Saved. Next movie.`
Responsive geometry had no horizontal overflow at 320 by 844, 390 by 568, 390 by 844, or 430 by 844.
The 200-percent-equivalent 195-pixel viewport reflowed without horizontal overflow.
Reduced motion and forced-colors media queries were active under emulation.
Primary captures are stored beside this file.

The failure-state Retry and Keep on this phone interaction is covered by the retained-draft implementation and focused contract test, but a live induced network-failure click-through was not captured.

## Decision

Builder handoff for independent review.
No acceptance claim.
