# MovieLens Support-Aware Hybrid Search

Date: 2026-07-11.
Phase: Recommendation Model Improvement.
Issue: #129.
Fit role: Development fit only.
Selection role: Development tune only.
Internal test opened: No.

## Result

The predeclared eight-candidate search selects blend shrinkage `80` instead of the refit reference value `10`.
On 2,923 tune-established users, the selected challenger improves NDCG@5 over the refit hybrid by 0.003425 with a paired 95% interval from 0.000423 to 0.006301.
The improvement is statistically credible but only 0.34 points, far below the locked 2.00-point quality-route threshold.

This is a frozen challenger for the shared internal test, not a new champion.
Hybrid remains the quality champion until issue #131 applies the two-gate protocol.

## Controlled Search

The search declared shrinkage values `1`, `2`, `5`, `10`, `20`, `40`, `80`, and `160` before tune evaluation.
Every candidate uses the same label-free development-fit manifest, 2,395,300 training ratings, 49,299 learned collaborative items, 285-column content snapshot, regularization, support cap, candidate pools, metrics, and seed.
Training includes 10,187 unique authorized profiles: the 8,770 established fit users plus cold-start-only diagnostic users assigned to the same fit role.
Selection uses the 2,923 tune-established users, while tune cold-start and deep-history memberships remain diagnostics.

The refit collaborative and every hybrid candidate receive the larger development-fit population.
The challenger therefore does not gain an unfair data-volume advantage over the refit incumbent recipe.

Selection uses tune-established NDCG@5, then pairwise preference accuracy, then smaller distance from the reference shrinkage.
No internal-test membership or labels influenced selection.

## Tune Evidence

Selected shrinkage `80` minus refit shrinkage `10` on established users:

- NDCG@5: `0.003425 [0.000423, 0.006301]`.
- Pairwise preference accuracy: `0.000991 [-0.000857, 0.003040]`.
- Known-dislike rate@5: `-0.000411 [-0.002874, 0.002121]`, where lower is better.
- Coverage: no change.

Selected shrinkage `80` minus refit collaborative on established users:

- NDCG@5: `0.006773 [0.003169, 0.010233]`.
- Pairwise preference accuracy: `0.005695 [0.002984, 0.008641]`.
- Known-dislike rate@5: `-0.003626 [-0.006774, -0.000205]`.
- Coverage: `0.007253 [0.006192, 0.008439]`.

## Support Cohorts

The selected hybrid's largest established support-bucket point estimate versus collaborative is on sparse items with five or fewer fit observations: 0.026061 NDCG@5.
That sparse estimate uses only 79 users and its interval from -0.017520 to 0.069178 crosses zero.
It is therefore a useful modeling clue rather than promotion evidence.

Established dense items show a smaller but repeatable 0.005956 NDCG@5 gain over collaborative with an interval from 0.002668 to 0.009289.
Unseen and sparse subgroup estimates remain visibly uncertain because their eligible sample sizes are small.

## Artifacts And Reproduction

Selected hybrid SHA-256: `8c470052641416e371bcadf195c202b0ea9a074eae82e2e7769e17641963a0bb`.
Refit collaborative SHA-256: `cd7a5eb0e3ce8980ef53e9d0fc76625cb804e5def37af5b90cc3bd224d465fad`.
Content snapshot SHA-256: `afc43ac51a6b55629930db862fff840a5c7c37b2b829df11fc75ac82c53942eb`.

The complete run took 306.906 seconds and peaked at 1,471.45 MB.
Per-user candidate rows remain in ignored local research storage.
The committed JSON contains aggregates, configuration, runtime, and checksums only.

Run `pnpm eval:movielens:support-aware` to reproduce the search.
Run `pnpm eval:movielens:support-aware:verify` to rebuild only the selected configuration and verify its checksum.

## Next Decision

Issue #130 may independently freeze one stronger ratings-only challenger.
Issue #131 will open the shared internal test once for the frozen issue #129 and #130 candidates, hybrid, collaborative, and V2.
If shrinkage `80` does not clear a champion-selection route, the small tune gain remains recorded and hybrid remains champion.
