# Scoring V2 Slice 12 Dogfood

Date: 2026-07-09
Phase: Scoring V2: Live Latency And Phone-Sized Dogfood Gate
Status: passed locally

## Phase Tracker

```text
Scoring V2: [####################] 14/14 issues done
```

## What Ran

- `pnpm eval:scoring-v2:compare`
- `pnpm build:web`
- `pnpm check`
- `MOBILE_UX_SMOKE_DEBUGGING_URL=http://127.0.0.1:9222 MOBILE_UX_SMOKE_EXPECT_V2_EXPLANATION=1 pnpm smoke:ux:mobile`
- `MOVIE_NIGHT_RECOMMENDATION_SOURCE=live_tmdb MOVIE_NIGHT_SCORING_ENGINE=v2_contract MOBILE_UX_SMOKE_DEBUGGING_URL=http://127.0.0.1:9222 MOBILE_UX_SMOKE_EXPECT_API=1 MOBILE_UX_SMOKE_EXPECT_RECOMMENDATION_SOURCE=live_tmdb pnpm smoke:ux:mobile`

## Live Latency

A direct live TMDb shortlist timing sample returned five V2 picks in 1.911 seconds.
The timing sample used `source=live_tmdb`, `scoringEngine=v2_contract`, `serviceConstraint=Prime Video`, and `availabilityRegion=Prime Video Germany`.
The returned titles were The Sheep Detectives, Project Hail Mary, Avatar: Fire and Ash, The Devil Wears Prada 2, and The Shawshank Redemption.

## Phone Dogfood Evidence

The live V2 phone smoke completed on a 390x844 viewport.
It created a backend session, loaded a live TMDb shortlist, completed both pass-the-phone reaction passes, loaded debug history, rendered the result explanation, added the best pick to the household watchlist, marked it watched, removed it, saved the session outcome, saved post-watch feedback for both participants, refreshed the profile ledger, and loaded the recent session detail.
The run used an existing Chrome DevTools endpoint instead of launching a new browser because local browser launch is unreliable in this sandbox.

## V1 Versus V2 Corpus Evidence

The comparison report is [docs/validation/scoring-v2-comparison.md](scoring-v2-comparison.md).
The fixed corpus has seven scenarios.
Current V2 shows one measurable improvement, six unchanged outcomes, and zero regressions under the current pass criteria.
The improvement is the no-strong-match scenario, where V2 now returns low confidence and a fallback reason.

## Wins

- V2 can be selected explicitly for live dogfood without changing the default V1 scorer.
- The live shortlist path stayed within a couch-usable latency range in the direct timing sample.
- The phone-sized flow rendered V2 evidence and completed the full follow-up loop.
- Post-watch feedback now refreshes the setup profile ledger before returning to a new night.

## Regressions

- No corpus regressions were recorded in the generated comparison report.
- The first live dogfood run exposed a real UI refresh gap for post-watch memory visibility, and that gap was fixed before the passing rerun.

## Remaining Risks

- This is still local dogfood, not founder acceptance of recommendation taste quality.
- Live quality depends on TMDb candidate supply as much as scorer behavior.
- Slice 13 recorded the founder promotion decision and V2 is now the default scorer for testing.

## Product Decisions

No product decision changed in this slice.
Watchability remains upstream of ranking.
Prime Germany rules remain unchanged.
Session modes remain unchanged.
V2 is the default scorer after the Slice 13 founder promotion decision.
V1 remains available as the rollback scorer.
