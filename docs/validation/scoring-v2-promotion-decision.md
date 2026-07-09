# Scoring V2 Promotion Decision Packet

Date: 2026-07-09
Phase: Scoring V2: V2 Default Promotion Decision
Status: founder approved V2 default for testing

## Phase Tracker

```text
Scoring V2: [####################] 14/14 issues done
```

## Decision Needed

The founder decision is to promote V2 as the default recommendation scorer for testing.
This remains a reversible product decision.

## Current Evidence

The fixed corpus comparison is [docs/validation/scoring-v2-comparison.md](scoring-v2-comparison.md).
The live dogfood note is [docs/validation/scoring-v2-slice-12-dogfood.md](scoring-v2-slice-12-dogfood.md).
The founder dogfood checklist is [docs/validation/scoring-v2-founder-dogfood-checklist.md](scoring-v2-founder-dogfood-checklist.md).
The research and architecture note is [docs/scoring-v2-data-research-spike.md](../scoring-v2-data-research-spike.md).
The slice plan is [docs/issues/scoring-v2-issue-breakdown.md](../issues/scoring-v2-issue-breakdown.md).

## Evidence Summary

- Fixed corpus scenarios: 7.
- V2 improvements: 1.
- V2 unchanged outcomes: 6.
- V2 regressions: 0 under the current pass criteria.
- Direct live TMDb V2 shortlist timing sample: 1.911 seconds for five picks.
- Live phone dogfood: passed on a 390x844 viewport.
- Default scorer after this decision: V2.
- V1 rollback path: set `MOVIE_NIGHT_SCORING_ENGINE=v1_heuristic`.

## Ranking Wins

V2 now exposes confidence and fallback behavior.
The no-strong-match scenario improved because V2 returns low confidence and a fallback reason instead of only returning a ranked list.
V2 also exposes richer dominant evidence such as profile concepts, metadata families, shared bridge value, and penalties.

## Ranking Concerns

Most fixed-corpus rankings are unchanged.
That is good for regression safety but weak as proof that V2 is materially better as the default today.
The high-confidence solo favorite scenario still ranks Arrival first, but V2 moves Loud Space Battle from rank 4 to rank 2.
That is not a pass-criteria regression, but it is a taste-quality warning worth founder review.

## Latency

The direct live V2 shortlist sample returned five picks in 1.911 seconds.
The full live phone smoke completed the pass-the-phone flow, debug history, watchlist actions, outcome saving, post-watch feedback, profile ledger refresh, and recent session detail.
This is acceptable for local dogfood, but it is not a replacement for founder-perceived couch speed.

## Explanation And Trust

V2 explanations are now visible in the result surface and debug history.
The UI can show why a title moved, what held it back, confidence, fallback state, and partial-support notes.
The review-mode phone smoke verifies V2-shaped explanation chips for profile evidence, candidate metadata, and penalties.

## Rollback Plan

V1 remains available as `v1_heuristic`.
If V2 is promoted and feels wrong, the app can switch back by restoring the default scorer to V1.
The current implementation now uses V2 by default and supports explicit V1 rollback testing.

## Recommendation

The founder chose to promote V2 as the default for testing.
The engineering evidence says V2 is safe enough to try live, explainable, and fast enough locally.
The main product risk remains taste quality, especially scenarios where V2 is unchanged rather than clearly better.

## Promotion Implementation

The default scorer changed from V1 to V2 in one small reversible edit.
The explicit V1 fallback path remains available.
Validation included `pnpm check`, `pnpm build:web`, and a live phone smoke with the default scorer path.
The default-path live phone smoke ran with `MOVIE_NIGHT_RECOMMENDATION_SOURCE=live_tmdb` and no `MOVIE_NIGHT_SCORING_ENGINE` override.
It passed on a 390x844 viewport with backend-backed debug history.

## Rollback Implementation

Set `MOVIE_NIGHT_SCORING_ENGINE=v1_heuristic` to force the legacy scorer during local testing.
If V2 feels wrong after tomorrow's founder test, change the API default back to `v1_heuristic`.

## Decision Record

Founder decision: promote V2 as the default scorer for testing.
Decision date: 2026-07-09.
Chosen path: promote.
Reason: the founder wants to go with V2 so far, land it on main, and test tomorrow.
Follow-up: founder will test the V2 default flow tomorrow and decide whether to keep, roll back, or revise.
