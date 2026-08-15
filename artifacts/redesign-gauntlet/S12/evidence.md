# S12 Round 3 Builder Evidence

## Claim

A valid five-movie shortlist never misrepresents whether the movies are live or whether the private round can be saved.

## Contract

Session state and the generation outcome now track `movieSource` separately from `persistenceSource`.
Live shortlist retrieval followed by shared-session failure produces `movieSource: live`, `persistenceSource: local`, and an explicit phone-only notice.
The existing exact-five gate remains unchanged.

## Boundary

The lifecycle owns source and recovery truth.
The reaction card only renders the resulting disclosure.
Recommendation ordering, persistence APIs, and the accepted generation presentation remain unchanged.

## Behavior

If neither live nor local supply can produce five, the app does not navigate, preserves setup, and offers Try again and Back to setup.
If five live movies are available but shared persistence is not, the app advances with those live movies and states that reactions are not saved.
Cleanup still finishes after the single allowed navigation.

## Evidence

- Focused S12 and S13 state tests: 12 of 12 passed.
- Full web state suite: 146 of 146 passed.
- Web TypeScript check: passed.
- Diff check: passed.
- Real 390 by 844 review fixture captured no-live/no-local failure with one dialog, Try again, Back to setup, and no navigation.
- Real 390 by 844 review fixture captured live Arrival data with the exact local-only persistence notice.
- Masked comparison metadata is in `masked-pair/metadata.json`.
- Full API and production build processes were still running during handoff and remain critic gates.

## Decision

Builder handoff only.
Independent acceptance remains required.
