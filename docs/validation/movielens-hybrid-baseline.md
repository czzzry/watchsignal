# MovieLens Content-Collaborative Hybrid Baseline

Date: 2026-07-10.
Phase: Recommendation Learning Lab.
Issue: #124.
Ratings and content fitting role: Exploration only.
Evaluation roles: Exploration and validation.
Sealed labels opened: No.
Live provider calls: Zero.
Machine-readable report: `docs/validation/movielens-hybrid-baseline.json`.
Model artifact and per-user rows: Ignored local research storage only.

## Claim

A fixed, versioned MovieLens content matrix can regularize and extend the selected ratings-only collaborative model without live metadata calls.
The first hybrid produces small but repeatable overall validation gains and substantially larger gains on a defensible sparse-item subgroup.
It does not reach the predeclared two-point effect across the full established, deep-history, or cold-start cohorts.

## Feature Snapshot

The local `movielens-content-v1` snapshot covers 87,585 movies with 285 numerical columns.
It contains no raw tags and no user histories.

| Family | Columns | Item coverage | Provenance | Treatment |
| --- | ---: | ---: | --- | --- |
| Genre | 19 | 91.92% | MovieLens `movies.csv` | Normalized multi-hot |
| Release era | 10 | 100.00% | Year parsed from MovieLens title | One-hot decade bucket |
| Semantic tags | 256 | 12.91% | 241,383 exploration-user tag rows at or before profile cutoff | L2-normalized TF-IDF, minimum five-movie support, top-256 vocabulary |
| Language | 0 | 0.00% | Not present in MovieLens 32M | Explicitly unavailable |
| Cast | 0 | 0.00% | Not present in MovieLens 32M | Reserved namespace `cast:actor` |
| Crew | 0 | 0.00% | Not present in MovieLens 32M | Separate reserved namespaces `crew:director` and `crew:writer` |

The implementation does not pretend that absent cast, crew, or language data exists.
No TMDb enrichment was fetched during evaluation.
If a later licensed snapshot adds people, actor, director, and writer identity cannot collapse into one undifferentiated person feature.

Content snapshot SHA-256: `afc43ac51a6b55629930db862fff840a5c7c37b2b829df11fc75ac82c53942eb`.

## Hybrid Method

The hybrid fits a weighted ridge map from genre, era, and tag features into the selected 16-dimensional collaborative movie space.
Training-item weights grow with collaborative support but are capped at 50 observations.
Genre and era coefficients use regularization 10, while high-cardinality tag coefficients use stronger regularization 50.

For each movie, the final representation blends its learned collaborative vector with its content-predicted vector.
The collaborative weight is `support / (support + 10)`.
Well-supported movies remain mostly collaborative, while sparse and unseen movies rely more heavily on content.

The artifact expands from 38,481 collaborative items to all 87,585 content-snapshot items.
It contains no user factors, histories, or raw tags.

Hybrid artifact SHA-256: `ab0a9622d31e0506ab91ec9be31fcbc3a7bf1a05a8360453df0b7dc92867d41a`.
An independent rebuild reproduced this checksum.

## Validation Results

| Cohort | Users | Hybrid NDCG@5 | Hybrid minus collaborative, 95% CI | Pairwise gain | Dislike@5 change | Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Cold start | 313 | 0.711513 | 0.003703 [-0.000635, 0.008044] | 0.005379 | 0.000000 | 1.000000 |
| Established | 5,000 | 0.607882 | 0.004368 [0.002659, 0.006197] | 0.005360 | -0.004080 | 1.000000 |
| Deep history | 1,956 | 0.601858 | 0.005851 [0.002206, 0.009141] | 0.008282 | -0.009509 | 1.000000 |

Established and deep-history gains are repeatable because their paired intervals remain above zero.
Cold-start improvement is inconclusive because its interval crosses zero.
Every overall gain is below one point and therefore below the locked two-point minimum useful effect.

The safety direction is favorable for established and deep-history users.
Known-dislike rate@5 falls by 0.004080 and 0.009509 respectively.

## Exploration Results

| Cohort | Users | Hybrid NDCG@5 | Hybrid minus collaborative, 95% CI | Dislike@5 change |
| --- | ---: | ---: | ---: | ---: |
| Cold start | 308 | 0.702946 | 0.004360 [-0.000503, 0.009150] | -0.003247 |
| Established | 4,617 | 0.598155 | 0.004611 [0.003055, 0.006327] | -0.003899 |
| Deep history | 1,883 | 0.567494 | 0.007223 [0.004233, 0.010103] | -0.001381 |

Exploration and validation agree on small established and deep-history gains and inconclusive cold-start gain.
That consistency makes the effect more credible, but it does not turn validation into sealed proof.

## Sparse-Item Results

Sparse items are future candidates with five or fewer collaborative training observations.
The reported subgroup includes only users with at least two sparse candidates and both positive and negative sparse labels.

| Role and cohort | Users | Sparse candidates | Hybrid NDCG@5 | NDCG gain, 95% CI | Dislike@5 change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Exploration established | 331 | 2,358 | 0.723771 | 0.029290 [0.007335, 0.052717] | -0.014502 |
| Exploration deep history | 354 | 3,844 | 0.661721 | 0.047915 [0.025649, 0.071221] | -0.040113 |
| Validation established | 335 | 2,307 | 0.727413 | 0.022342 [-0.000858, 0.045397] | -0.010149 |
| Validation deep history | 365 | 4,025 | 0.670938 | 0.046530 [0.023600, 0.069836] | -0.031233 |

Validation deep-history sparse items show the strongest evidence: a 4.65-point NDCG gain with an interval entirely above zero, plus lower dislike exposure.
Validation established has a 2.23-point estimate but remains inconclusive because its interval crosses zero.
Cold-start does not have a sufficient both-label sparse subgroup and is not reported as if it did.

## Contribution Diagnostics

The artifact retains separate contribution arrays for collaborative, content intercept, genre, era, and tags.
For validation established top-five recommendations, mean absolute contribution magnitudes are:

- Collaborative: 0.750515.
- Tags: 0.014977.
- Genre: 0.007795.
- Era: 0.006212.
- Content intercept: 0.003957.

These magnitudes support debugging but do not prove causal feature value.
Tags may have the largest numerical content contribution while still being redundant or harmful after other families are present.
Issue #125 therefore removes one family at a time and retrains rather than interpreting coefficient magnitude as ablation evidence.

## Runtime And Engineering Finding

The successful full run took 387.439 seconds, or about 6.5 minutes.
Hybrid ridge fitting took 1.285 seconds and paired model evaluation took 29.670 seconds.
The remaining time covers protected archive passes, snapshot loading, deterministic artifact compression, sparse subgroup construction, and 1,000-resample intervals.
Peak memory was 878.46 MB.

An initial run exposed a performance bug where each user rebuilt 38,000-item and 87,000-item lookup dictionaries.
The indexes are now cached once per immutable model, and regression tests assert object reuse.
This optimization changed runtime behavior only, not users, candidate pools, metrics, or model scores.

Run `pnpm eval:movielens:content-snapshot` to rebuild the fixed feature snapshot.
Run `pnpm eval:movielens:hybrid` to fit and evaluate the first hybrid.
Run `pnpm eval:movielens:hybrid:verify` to reproduce the artifact checksum.

## Limits And Next Move

The current snapshot cannot test language, cast, director, or writer value because those families have no licensed fixed local coverage.
The tag family has only 12.9% item coverage and may help a narrow subset while adding complexity.
The overall improvement is statistically repeatable but too small to justify promotion by itself.

Issue #125 must retrain controlled family ablations, compare quality, safety, coverage, runtime, and sparse-item behavior, and select exactly one checksum before any sealed label is opened.
