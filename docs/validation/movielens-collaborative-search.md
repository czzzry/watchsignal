# MovieLens Collaborative And Ranking Candidate Search

Date: 2026-07-11.
Status: Candidate frozen for shared internal-test selection.

## Decision

The bounded tune search selected `als_d16_r2_i5` from 12 predeclared candidates.
The internal-test labels remained unopened.
This candidate is frozen for issue #131 and is not a product-default decision.

## Established Tune Evidence

Against the same-data explicit-ALS reference, the selected candidate changed NDCG@5 by 0.011004, with a paired 95% interval from 0.008429 to 0.013626.
Against the frozen support-aware hybrid, the selected candidate changed NDCG@5 by 0.004231, with a paired 95% interval from 0.000925 to 0.007393.

## Interpretation

The weighted objective is a ranking-aligned squared-error surrogate that gives strong likes and dislikes more influence during fitting.
It is not a pairwise BPR objective and the report does not describe it as one.
Tune performance selects a candidate for one shared internal test; it does not establish an independent final claim.

## Reproducibility

The selected artifact SHA-256 is `d6858942711fe929858c9143c8ca419952be9f135addd3f9b9694ac2294a344b`.
The full experiment took 683.476 seconds and recorded peak process memory of 864.85 MB.
