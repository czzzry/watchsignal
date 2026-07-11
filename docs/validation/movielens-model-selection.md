# MovieLens Feature Ablation And Model Selection

Date: 2026-07-10.
Phase: Recommendation Learning Lab.
Issue: #125.
Selection data: Validation only.
Sealed labels opened: No.
Machine-readable selection record: `docs/validation/movielens-model-selection.json`.

## Decision

Select the full genre, era, and tag hybrid for the one-time sealed benchmark.

Selected artifact SHA-256: `ab0a9622d31e0506ab91ec9be31fcbc3a7bf1a05a8360453df0b7dc92867d41a`.
Selection record SHA-256: `ec0cd1b9e67214fdb106c611a3ce2387d42bf816f02b2437fa3c47eba1eec04f`.

The artifact was selected and checksummed before any sealed label was opened.
The checksum matches the independently reproduced full-hybrid artifact from issue #124.

## Controlled Experiment

Every variant uses the same 1,268,600 exploration training ratings, collaborative artifact, content snapshot, validation users, candidate pools, blend shrinkage, support cap, regularization values, seed, metrics, and 1,000-resample user-level intervals.
One declared family changes per retrain.

| Variant | Included families | Validation established NDCG@5 | Pairwise accuracy | Dislike@5 | Coverage |
| --- | --- | ---: | ---: | ---: | ---: |
| Collaborative only | None | 0.603514 | 0.762530 | 0.081360 | 0.989020 |
| Full hybrid | Genre, era, tags | 0.607882 | 0.767891 | 0.077280 | 1.000000 |
| Without genre | Era, tags | 0.608105 | 0.765278 | 0.077400 | 1.000000 |
| Without era | Genre, tags | 0.607050 | 0.767131 | 0.077320 | 1.000000 |
| Without tags | Genre, era | 0.607886 | 0.766969 | 0.077120 | 1.000000 |

## What Each Family Contributes

The family effect is the paired ablated-minus-full result.
A negative value means removing the family made the metric worse.

| Removed family | Established NDCG delta, 95% CI | Established pairwise delta, 95% CI | Deep NDCG delta, 95% CI |
| --- | ---: | ---: | ---: |
| Genre | 0.000223 [-0.000517, 0.001024] | -0.002613 [-0.003452, -0.001807] | 0.000600 [-0.000787, 0.001987] |
| Era | -0.000831 [-0.001606, -0.000079] | -0.000759 [-0.001268, -0.000202] | -0.000273 [-0.001447, 0.001033] |
| Tags | 0.000005 [-0.000859, 0.000875] | -0.000921 [-0.001562, -0.000293] | 0.000001 [-0.001612, 0.001568] |

Era supplies a small repeatable established NDCG and pairwise benefit.
Genre and tags do not move established NDCG reliably, but removing either causes a repeatable pairwise-ordering loss.
No available family individually approaches the two-point minimum useful effect.

The result also demonstrates why coefficient magnitude was not enough.
Tags had the largest content contribution magnitude in issue #124, but removing tags leaves NDCG effectively unchanged while slightly weakening pairwise ordering.
Only retraining the ablation reveals that distinction.

## Selection Rule Correction

The first automatic selector considered NDCG mean alone and provisionally chose the no-genre variant from a 0.000223 mean advantage.
That was inconsistent with the locked protocol because NDCG@5 and pairwise preference accuracy are co-primary metrics.

Before sealed access, the selector was corrected and regression-tested.
An ablation may displace the full model only if both established NDCG and pairwise paired intervals versus full have non-negative lower bounds and the dislike guardrail passes.
No ablation satisfies that condition.

This correction did not inspect sealed data and did not change any model scores.
It aligned the automated decision with the already-locked metric contract.

## Baseline Ladder

Validation-established NDCG@5 remains visible for every major approach:

| Approach | NDCG@5 |
| --- | ---: |
| V2 heuristic | 0.449374 |
| V1 heuristic | 0.450406 |
| Popularity | 0.600178 |
| Ratings-only collaborative | 0.603514 |
| Full hybrid | 0.607882 |

The full hybrid is the validation winner, but its gain over collaborative is only 0.004368 and remains below the two-point minimum useful effect.
Selection for sealed evaluation is not the same as approval for product promotion.

## Safety, Coverage, Confidence, And Cost

The full hybrid improves validation-established dislike@5 from 0.081360 to 0.077280 and coverage from 0.989020 to 1.000000 versus collaborative.
No available ablation violates the one-point dislike guardrail.

The offline learned models do not emit a product confidence label.
The selection packet reports cohort intervals and profile and candidate coverage rather than inventing confidence semantics.
Product integration must still expose sparse or unsupported evidence honestly.

The complete ablation run took 364.556 seconds and peaked at 1,044.43 MB.
Individual hybrid variants fit in 0.35 to 1.22 seconds and evaluated the three validation cohorts in roughly five to six seconds after local data preparation.

## High-Cardinality And Missing Families

Tags retain 256 columns, 12.91% item coverage, minimum five-movie support, and ridge regularization 50 versus 10 for genre and era.
This controls but does not eliminate sparse-tag risk.

Language, cast, and crew have zero fixed-snapshot columns and are marked not testable.
Actor, director, and writer namespaces remain separate.
No claim is made about families that the dataset cannot test.

## Sealed Handoff

Issue #126 may open the sealed manifest only if the selected artifact checksum is exactly `ab0a9622d31e0506ab91ec9be31fcbc3a7bf1a05a8360453df0b7dc92867d41a` and a sealed-access event is recorded.
Popularity, V1, V2, collaborative, and the selected full hybrid must run once through the unchanged sealed evaluator.
No feature, parameter, or model choice may change after seeing those results.
