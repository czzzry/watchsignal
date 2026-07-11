# MovieLens Founder Decision Addendum

Date: 2026-07-11.
Original protocol date: 2026-07-10.
Original sealed benchmark issue: #126.
Status: Post-result decision clarification.

## Why This Addendum Exists

The original benchmark and its results remain unchanged.
After the sealed result was opened, the founder clarified that the intended product question had been understood as whether a learned recommender materially improves on the deployed V2 heuristic.
The locked promotion rule instead tested whether the selected hybrid materially improves on the strongest available comparator, which proved to be the ratings-only collaborative model.

This addendum records that difference without rewriting the original hypothesis, threshold, comparator rule, or result.

## Original Confirmatory Question

The locked protocol asked whether the selected hybrid beats the strongest comparator while satisfying quality, safety, coverage, and practical-effect gates.
The strongest comparator was collaborative.

Hybrid improved established-user NDCG@5 over collaborative by 0.005553, with a 95% interval from 0.003863 to 0.007349.
The gain was statistically credible but below the predeclared 0.02 minimum useful improvement.
The automated **hold** recommendation therefore remains the correct confirmatory outcome.
The project does not claim that hybrid passed the original practical-effect gate.

## Separate Product Question

The deployed control is V2 rather than collaborative.
On the sealed established cohort, hybrid scored 0.612361 NDCG@5 and V2 scored 0.452318.
The 0.160043 absolute difference is substantial on the measured individual future-rating task.
Collaborative also substantially outperformed V2, which shows that most of the improvement came from learned ratings structure rather than the hybrid content layer alone.

This evidence supports testing a learned individual-taste provider inside the product.
It does not prove that the complete hybrid product path is better for two-person compromise, tonight intent, availability, explanation quality, or household satisfaction because MovieLens does not measure those outcomes.

## Founder Decision

The founder chose to promote hybrid from research artifact to reversible product-integration candidate.
This is not a retroactive pass of the original hybrid-versus-collaborative practical-effect gate.
It is a separate product decision based on the large learned-model gain over the deployed V2 taste heuristic, the hybrid's highest overall sealed score, favorable safety and coverage, sparse-item evidence, and manageable incremental complexity.

Issue #127 remains the required household gate.
It must compare the current V2 path, V2 household logic fed by collaborative individual scores, and V2 household logic fed by hybrid individual scores before any default changes.

## Scientific Claims We May Make

- Hybrid achieved the highest sealed MovieLens NDCG@5 among the evaluated approaches.
- Hybrid and collaborative substantially outperformed V2 on the individual future-rating benchmark.
- Hybrid produced a statistically credible 0.005553 NDCG@5 gain over collaborative.
- Hybrid did not clear the predeclared 0.02 practical-effect threshold over collaborative.
- The MovieLens result justifies reversible product integration and household evaluation, not an unconditional claim of household superiority.

## Claims We Must Not Make

- The original promotion gate passed.
- The two-point threshold was defined against V2.
- Hybrid has already proven better household recommendations.
- The sealed panel remains untouched independent evidence for future tuning.
- A future model may reuse this sealed panel for another confirmatory claim.

## Forward Rule

Future protocols must name the deployed control, simplicity baseline, quality champion, and promotion comparator separately.
They must also distinguish model-selection gates from product-deployment gates before training begins.
The next model-improvement protocol in #128 will apply that terminology explicitly.
