# MovieLens Cohort Baselines

Date: 2026-07-10.
Phase: Recommendation Learning Lab.
Issue: #122.
Roles opened: Exploration and validation only.
Sealed labels opened: No.
Machine-readable report: `docs/validation/movielens-cohort-baselines.json`.
Detailed per-user report: Ignored local research storage only.

## Claim

Random order, a leakage-controlled popularity baseline, unchanged V1, and unchanged V2 now run through the same MovieLens candidate and future-label contract across protected exploration and validation cohorts.
Metrics are calculated per user before aggregation and include deterministic user-level percentile bootstrap intervals.

This report establishes baselines for later learned models.
It does not promote V1, V2, or popularity into the product.

## Baseline Contract

The random baseline uses a deterministic hash of the protocol seed, cohort, user, and candidate identifier.
The popularity baseline trains only on 461,700 profile rows from exploration-established users and never consumes future labels.
When an exploration user is evaluated, that user's own popularity contribution is removed before ranking.
This leave-one-user-out rule prevents the user's later history from leaking into an earlier cold-start or profile-depth result.

V1 and V2 are the unchanged production scorers.
They receive the same application-native profile, session, and candidate contract.
Every model ranks the same future-rated candidate pool for a given user.

## Primary Results

NDCG@5 means are shown below.
Every value is the mean of per-user metrics rather than one metric calculated after pooling all rows.

| Role and cohort | Users | Random | Popularity | V1 | V2 | V2 minus V1, 95% CI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Exploration cold start | 308 | 0.539876 | 0.702329 | 0.578755 | 0.575590 | -0.003165 [-0.012111, 0.007151] |
| Validation cold start | 313 | 0.554220 | 0.723535 | 0.586754 | 0.587682 | 0.000929 [-0.007851, 0.010506] |
| Exploration established | 4,617 | 0.429225 | 0.600184 | 0.450803 | 0.449429 | -0.001374 [-0.002292, -0.000397] |
| Validation established | 5,000 | 0.428572 | 0.600178 | 0.450406 | 0.449374 | -0.001032 [-0.001798, -0.000329] |
| Exploration deep history | 1,883 | 0.364816 | 0.568065 | 0.388282 | 0.387432 | -0.000850 [-0.002329, 0.000710] |
| Validation deep history | 1,956 | 0.358139 | 0.573171 | 0.388845 | 0.388999 | 0.000153 [-0.001167, 0.001506] |

V2 does not beat V1 on the locked two-point target.
On established users, the paired intervals indicate a small but repeatable V2 regression rather than an improvement.
Cold-start and deep-history NDCG differences are inconclusive because their intervals include zero.

Popularity beats V1 and V2 by a large margin in every reported group.
This establishes a serious baseline for the collaborative and hybrid models rather than proving that popularity is the right WatchSignal product strategy.

## Pairwise Preference And Safety

| Role and cohort | Popularity pairwise | V1 pairwise | V2 pairwise | V1 dislike@5 | V2 dislike@5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Exploration cold start | 0.737190 | 0.580355 | 0.578982 | 0.212338 | 0.216234 |
| Validation cold start | 0.739979 | 0.551462 | 0.552442 | 0.196166 | 0.198083 |
| Exploration established | 0.743233 | 0.552625 | 0.549447 | 0.148062 | 0.149188 |
| Validation established | 0.746438 | 0.546035 | 0.543221 | 0.149960 | 0.150520 |
| Exploration deep history | 0.763390 | 0.533312 | 0.531295 | 0.177058 | 0.176314 |
| Validation deep history | 0.772612 | 0.537654 | 0.536947 | 0.182413 | 0.182106 |

V2's established known-dislike regression is 0.001126 in exploration and 0.000560 in validation.
Both remain well inside the locked maximum regression of 0.01, but neither is an improvement.

## Paired Profile-Depth Learning Curve

The cohort rows above are not a clean learning curve because cohort membership and future candidate count change along with profile depth.
The additional paired experiment holds all 3,839 deep-history users and their final 50 future candidates constant, then varies only the immediately preceding profile evidence from 10 to 100 to 500 ratings.

| Role | Profile ratings | V1 NDCG@5 | V2 NDCG@5 | V2 gain versus 10, 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Exploration | 10 | 0.382138 | 0.382206 | 0.000000 [0.000000, 0.000000] |
| Exploration | 100 | 0.391483 | 0.390543 | 0.008337 [-0.000297, 0.016648] |
| Exploration | 500 | 0.388282 | 0.387432 | 0.005227 [-0.003231, 0.014573] |
| Validation | 10 | 0.385126 | 0.383734 | 0.000000 [0.000000, 0.000000] |
| Validation | 100 | 0.391782 | 0.392395 | 0.008661 [0.000919, 0.016412] |
| Validation | 500 | 0.388845 | 0.388999 | 0.005265 [-0.002646, 0.013154] |

One hundred profile ratings improve V2 over 10 on validation, but the gain is below the locked two-point target.
Five hundred ratings do not reliably improve over 10 and score below 100 ratings.
The current heuristic therefore does not convert additional evidence into monotonically better predictions.
One plausible explanation is signal dilution: all history contributes to broad title and genre affinities without a learned mechanism for recency, latent taste structure, or evidence weighting.
The collaborative and hybrid model issues will test whether trained representations use deeper history more effectively.

## Denominators And Exclusions

| Role and cohort | Users | Neutral labels excluded from pairwise comparisons | Missing movie identifiers |
| --- | ---: | ---: | ---: |
| Exploration cold start | 308 | 772 | 0 |
| Validation cold start | 313 | 742 | 0 |
| Exploration established | 4,617 | 48,605 | 0 |
| Validation established | 5,000 | 51,715 | 0 |
| Exploration deep history | 1,883 | 37,434 | 0 |
| Validation deep history | 1,956 | 38,136 | 0 |

All models achieved complete candidate coverage on the eligible rows.
Neutral labels remain available to NDCG as graded relevance but are excluded from the explicitly positive-versus-negative pairwise metric.

## Confidence Behavior

V1 marked no eligible users uncertain because every mapped profile contained onboarding-equivalent taste evidence.
V2 marked every user uncertain and reported mean confidence near 0.44 under the title-and-genre MovieLens adapter.
This is evidence that V2's confidence contract does not interpret its narrow score separations as strong support in this offline setting.
It should not be silently converted into high-confidence evidence.

## Runtime And Reproduction

The first uncached full run completed 14,077 user-cohort evaluations in 1,938.266 seconds, or about 32.3 minutes.
Peak memory was 138.93 MB on Python 3.13.1 for macOS x86_64.
The paired depth curve added 3,839 user rows in 395.211 seconds.

Mean per-user V2 scorer time was 2.50 ms for validation cold start, 22.33 ms for validation established, and 148.71 ms for validation deep history.
Mean V1 time for those same groups was 1.38 ms, 18.06 ms, and 133.99 ms.
The remaining wall time includes two archive passes, profile and candidate adaptation, report assembly, and 1,000-resample bootstrap intervals.

Run `pnpm eval:movielens:baselines` to reproduce the full baseline from local research data.
Run `pnpm eval:movielens:depth-curve` after the baseline to reproduce the paired depth analysis.
The stable aggregate fingerprint is `4324fea79f87989a6ebf4efbc20e21fb8aa791ded332cc8e147746b31e60870f`.
The stable depth-curve fingerprint is `2752f8cb456d7bc56788d92f79f70e2aa1a6be530b2d30275adc8f6cd4b54b7a`.

## Limits

MovieLens future-rated candidates are movies users chose to rate, not a random sample of every movie they could have ignored.
That selection bias can make a popularity baseline especially strong and does not reproduce catalog retrieval, current availability, tonight intent, or household compromise.
The baseline still matters because every later model receives the same selected-candidate contract and must clear the same bar.

The detailed per-user metrics remain in ignored local storage to avoid redistributing MovieLens-derived individual records.
The committed report publishes aggregate metrics, denominators, intervals, runtime, and stable fingerprints only.
