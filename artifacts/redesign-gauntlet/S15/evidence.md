# S15 Outcome and post-watch evidence

## Claim

After-tonight feedback is available progressively from the result and records watched winner, watched other, or nothing without cluttering the result or saving incomplete feedback.

## Contract

Watched winner binds to the top ranked movie.
Watched other must bind to a current shortlist movie.
Nothing watched has no selected title.
Profile feedback is available only after a watched title has persisted, requires every participating profile, and rejects profiles outside the session.
Duplicate outcome and feedback submissions are locked.

## Boundary

`OutcomeUtility` owns the compact after-tonight presentation.
`outcome-contract` owns save eligibility and title selection.
`useResultsPersistence` owns API calls, draft retention, duplicate guards, and saved state.
Ranking, result presentation, and API schemas are unchanged.

## Behavior

The user chooses one of three outcomes, optionally adds a note, and saves once.
If a title was watched, each profile then receives a separate Loved, Fine, or No rating and optional note.
Failure copy explicitly says the choices remain and exposes Retry.
Disconnected sessions remain visible but cannot imply a durable save.

## Evidence

Focused contract suite: 7 tests passed in round 2.
The suite covers all three outcome values, shortlist integrity, no-feedback-without-watched-title, full participant completion, retained failure drafts, retry, duplicate locks, wrong-profile guards, poster fallback, 12px text floor, 44px targets, short-height rule, focus, reduced motion, reduced transparency, and forced colors.
Round 2 proves that unchanged saved feedback cannot submit again, editing any rating or note invalidates only that profile's saved confirmation, and a partial failure retries only unresolved profiles.
The API's profile and title keyed upsert remains the durable duplicate guard if a response is lost after persistence.
Type, full state, API, and production build results are recorded in the builder handoff.
Real 320, 390, and 430 browser captures remain unproven if no browser session is available to the builder and must be checked by the independent critic.

## Decision

Builder handoff for independent review.
No acceptance claim.
