# S13 Round 3 Builder Evidence

## Claim

Two successive continuation rounds preserve confirmed direction, exclusions, and every prior solo reaction while producing five fresh movies each time.

## Contract

Local solo reaction history is accumulated by movie identity before each successful batch reset.
The next shortlist request receives the cumulative history, all shown movie IDs, and only confirmed Tonight intent.
Confirmed language filters use ISO 639-1 values and reach TMDB discovery through `with_original_language`.

## Boundary

The session controller owns local reaction accumulation.
The lifecycle owns the next shortlist request.
The intent interpreter owns language mapping, while TMDB discovery owns applying the resulting language constraint.
Ranking ownership and recommendation ordering are unchanged.

## Behavior

A confirmed French steer maps to `filters.language: fr` and the third-batch request retains it.
After two successful batches, the third request has ten unique exclusions and ten accumulated solo reactions.
Each returned batch must still contain exactly five unique movies with no repeats.
Only one clarification remains permitted.

## Evidence

- Focused S12 and S13 state tests: 12 of 12 passed.
- Full web state suite: 146 of 146 passed.
- Web TypeScript check: passed.
- Diff check: passed.
- Deterministic integration test performs two successful continuation calls and asserts the third request has ten exclusions, ten reactions, and one confirmed French intent.
- Deterministic API tests cover French intent interpretation, request-contract mapping, and TMDB discovery parameter mapping.
- Disabled Review contrast is explicit rather than opacity-based, and 568-pixel short-height spacing is bounded.
- Masked comparison metadata is in `masked-pair/metadata.json`.
- Full API and production build processes were still running during handoff and remain critic gates.

## Decision

Builder handoff only.
Independent acceptance remains required.
