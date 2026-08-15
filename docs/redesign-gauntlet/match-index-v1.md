# Match Index v1 contract

## Decision

Implement a frontend presentation calibration that removes the misleading percentage and preserves ranking evidence.
Do not change recommender weights or API ordering in this slice.
Do not force rank gaps or normalize one five-movie shortlist against itself.

## Diagnosis

The current UI renders the bounded `groupScore` as a percentage after adding current-session reaction bonuses.
A couple can add up to 0.24 to a score that is already bounded at one.
The client then clamps the combined value and clips the display at 99, which collapses distinct high-scoring titles into repeated 96 to 99 values.
The number is a recommendation signal, not a probability.

The current client also weights reaction bonuses by session mode.
That disagrees with the shared-session backend, which stores a mode-aware profile score and then adds both participants' reactions equally when it reranks.

Disconnected demo candidates without `groupScore` currently share one universal fallback.
That makes identical reactions produce identical visible scores even when the existing fixture taste signals differ.

## Function contract

```ts
type MatchIndexBreakdown = {
  scoreKind: "match_index_v1";
  score: number;
  exactScore: number;
  baseSignal: number;
  reactionDeltaRaw: number;
  combinedRaw: number;
  rawMinimum: -0.36 | -0.18;
  rawMaximum: 1.24 | 1.12;
};

calculateMatchIndex({
  modelScore,
  peopleMode,
  founderReaction,
  wifeReaction,
}): MatchIndexBreakdown
```

Clamp `modelScore` to the model's declared zero-to-one domain before applying reactions.

Reaction values remain:

- Interested adds 0.12.
- Maybe adds 0.04.
- No subtracts 0.18.
- A missing reaction adds zero.

For a couple, `reactionDeltaRaw` is the founder reaction plus the wife reaction.
This matches backend shared-session reranking because session mode is already represented in the stored profile score.
For a solo session, use only the active participant's reaction.

`combinedRaw` is `clamp(modelScore, 0, 1) + reactionDeltaRaw` and remains unclamped.
The unclamped value owns local sorting, exact ties, and lead gaps.

Map the complete reachable domain through one fixed affine scale:

- Couple: `exactScore = ((combinedRaw + 0.36) / 1.60) * 100`.
- Solo: `exactScore = ((combinedRaw + 0.18) / 1.30) * 100`.

Clamp only floating-point noise after the affine transform.
Round once to create the displayed integer `score` using deterministic half-up rounding with a fixed floating-point tolerance.

```ts
const SCORE_ROUNDING_EPSILON = 1e-10;
const score = Math.floor(exactScore + 0.5 + SCORE_ROUNDING_EPSILON);
```

The tolerance corrects binary floating-point noise at a true half boundary without moving a value that is meaningfully below that boundary.

## Ranking invariants

- API `rerankedSourceMovieIds` remains authoritative when present.
- Without API reranking, order by unrounded `combinedRaw`, then by the original base rank.
- The transform is monotonic over the entire reachable domain.
- Identical raw inputs stay tied.
- Different raw inputs never become exact ties because of clipping.
- Rounded display ties are allowed and do not become exact ties.
- Never alter ranking to make the visible gaps look larger.
- Log a development-only diagnostic when authoritative API order contradicts `combinedRaw`.

## Demo fallback

When a disconnected demo candidate lacks `groupScore`, derive its base score from the fixture's two individual taste values using the same backend group formula and current session mode.
Do not keep the universal 0.72 default.

## Lead language

Calculate the lead from unrounded exact scores.

- An exact tie is `Tied on match signal`.
- A positive gap below one is `<1 point clear`.
- A larger gap uses the floored exact difference, such as `12 points clear`.
- A single result is `Only match`.
- An active alternative describes its exact distance behind the leader.

## UI semantics

- Render an integer with the small label `match`.
- Never append `%` or call the index a probability or confidence.
- Session-level recommendation confidence remains a separate signal and does not feed this index.
- Do not show internal model values in the ordinary household experience.
- Retire `Epic`, `Strong`, and `Warm` labels because their old thresholds inherit the misleading percentage semantics.
- Remove percent suffixes from every household-facing winner and backup surface.
- The golden 84, 72, 61, 52, and 38 values are visual examples and must never be forced onto production data.

## Correct test vectors

| Case | Inputs | Exact index | Display |
| --- | --- | ---: | ---: |
| Couple, both interested A | base 0.80, reaction 0.24 | 87.50 | 88 |
| Couple, both interested B | base 0.73, reaction 0.24 | 83.13 | 83 |
| Couple, both interested C | base 0.60, reaction 0.24 | 75.00 | 75 |
| Couple near tie A | base 0.8005, reaction 0.24 | 87.53 | 88 |
| Couple near tie B | base 0.8001, reaction 0.24 | 87.51 | 88 |
| Couple, one Interested and one No | base 0.72, reaction -0.06 | 63.75 | 64 |
| Couple, both Maybe | base 0.72, reaction 0.08 | 72.50 | 73 |
| Solo Interested | base 0.72, reaction 0.12 | 78.46 | 78 |
| Solo Maybe | base 0.72, reaction 0.04 | 72.31 | 72 |
| Solo No | base 0.72, reaction -0.18 | 55.38 | 55 |
| Solo only result | base 0.62, reaction 0.12 | 70.77 | 71 |
| Couple weak double No | base 0.10, reaction -0.36 | 6.25 | 6 |
| Couple theoretical minimum | base 0, reaction -0.36 | 0 | 0 |
| Couple theoretical maximum | base 1, reaction 0.24 | 100 | 100 |

Also test identical raw inputs, distinct double-No inputs, rounded display ties, backend reaction parity, solo identity ownership, one candidate, no candidates, and malformed model-score clamping.
Add explicit rounding-boundary tests for an exact `.5`, a value below `.5` by more than the tolerance, and a value above `.5`.

## Evaluation gate

- API movie order is identical before and after the presentation change.
- No adjacent exact-score inversion occurs.
- Identical raw scores remain exact ties.
- Rounded display ties retain their unrounded ordering.
- Display gaps equal the fixed affine transformation of raw gaps.
- The complete theoretical input domain has no lower or upper clipping before transformation.
- No household Match Index surface contains a percent suffix.
- Every named vector passes.
- One canonical shared-session rerank proves backend and client reaction parity.
- A blind result-screen comparison prefers the new presentation for credibility without a functional regression.

Do not rerun MovieLens or claim recommendation-quality improvement because this contract intentionally preserves ranking.

## Recommender follow-up trigger

Instrument exact backend saturation separately.
If live replay contains multiple candidates with `groupScore` equal to one or authoritative API ordering conflicts with `combinedRaw`, open a recommender-contract slice that preserves an unclamped `rankingScoreRaw`.
Do not reconstruct information already lost to backend clipping through artificial UI gaps.
