# MovieLens sealed benchmark

## Decision status

The automated recommendation is **hold**.
The gain is credible but smaller than the minimum useful effect.
The founder subsequently chose **promote to reversible product integration**, not unconditional default promotion.
That decision reflects the hybrid's substantial gain over the current V2 heuristic, highest overall sealed NDCG@5, favorable safety and coverage, and sparse-item benefit.
The failed minimum-useful-effect gate still applies to the hybrid's incremental gain over collaborative, so the household gate remains mandatory before any default change.
The post-result distinction between the confirmatory outcome and product decision is recorded in `docs/validation/movielens-founder-decision-addendum.md`.

## Headline evidence

The decision cohort is `established` and the strongest comparator is `collaborative`.
Selected hybrid minus comparator NDCG@5 is 0.005553 with a 95% interval from 0.003863 to 0.007349.
Selected hybrid minus comparator pairwise accuracy is 0.005814.
Selected hybrid minus comparator known-dislike rate at 5 is -0.004640.

## Promotion gates

- `ndcg_statistically_positive`: pass
- `pairwise_non_regressing`: pass
- `minimum_useful_ndcg_gain`: fail
- `dislike_safety`: pass
- `coverage_parity`: pass

## Interpretation boundary

This benchmark evaluates one-person next-rating ranking on MovieLens.
It does not prove household compromise quality, tonight-specific intent, streaming availability, or real-product adoption.
A revision informed by these sealed results requires a fresh independent sealed panel.
The current result may support reversible integration and household evaluation without being represented as proof of complete product superiority.
