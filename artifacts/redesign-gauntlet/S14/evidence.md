# S14 Shared watchlist evidence

## Claim

The shared watchlist is reachable from the result without competing with the movie decision, and every movie can be saved, undone, rated, removed, or marked watched without locking unrelated entries.

## Contract

The household and source movie identity are validated before mutation.
Only profiles participating in the current session can contribute ratings.
Each entry owns its own duplicate-action lock and busy state.
Persistence outcomes use explicit saved, removed, local-only, or failed messages.

## Boundary

`ResultUtilityHub` owns progressive entry from the result.
`WatchlistUtility` owns loading, empty, list, rating, remove, and watched presentation.
`useResultsPersistence` owns API calls and transactional state.
Recommendation ranking, pass-the-phone flow, and API schemas are unchanged.

## Behavior

The result offers one dominant save action with Saved and Tap to undo confirmation.
The watchlist uses concise rows, missing-art fallback, per-profile rating controls, and one Mark watched action per movie.
Failures retain the current list and expose retry or honest connection copy.

## Evidence

Focused contract suite: 7 tests passed in round 2.
The suite covers household and entry validation, profile filtering, concurrent unrelated entry state, public result copy, required UI states, 12px text floor, 44px targets, focus, reduced motion, reduced transparency, and forced colors.
Round 2 proves that disconnected watchlists render an explicit unavailable state rather than genuine empty or an inert Retry action.
It also proves that a successful Mark watched action confirms once as Watched saved, blocks accidental duplicate submission, and becomes editable again only after that entry's ratings change.
Type, full state, API, and production build results are recorded in the builder handoff.
Real 320, 390, and 430 browser captures remain unproven if no browser session is available to the builder and must be checked by the independent critic.

## Decision

Builder handoff for independent review.
No acceptance claim.
