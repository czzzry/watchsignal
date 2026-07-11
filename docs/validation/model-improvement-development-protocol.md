# Model Improvement Development Protocol

Date: 2026-07-11.
Phase: Recommendation Model Improvement.
Issue: #128.
Decision owner: Founder.
Status: Approved before candidate training.

## Objective

Find the strongest defensible learned individual-taste model while preserving a repeatable way to improve it.
This protocol separates eligibility for product consideration from selection among learned models.
It does not train household reconciliation or change the product default.

## Model Roles

| Role | Model | Decision question |
| --- | --- | --- |
| Deployed control | V2 | Does learned recommendation materially improve on what the app uses today? |
| Simplicity baseline | Collaborative | Is added model and data complexity earning its cost? |
| Quality champion | Hybrid | Does a challenger improve on the best sealed ranking result so far? |
| Challenger | New candidate | Does it clear both eligibility and champion-selection rules? |

V2 is the product floor, not the only model-selection comparator.
Hybrid remains champion unless a challenger earns replacement under the rules below.

## Gate One: Learned-Model Eligibility

A challenger qualifies for product consideration only when all of these conditions hold on the primary established-user internal test:

- NDCG@5 improves over V2 by at least 0.02 absolute.
- The paired 95% confidence interval for NDCG@5 improvement over V2 has a lower bound above zero.
- Pairwise preference accuracy does not regress against V2.
- Known-dislike rate@5 does not regress by more than 0.01 absolute against V2.
- Candidate coverage is at least 0.98 and all fallback behavior is reported.

Clearing this gate does not make the challenger the preferred learned model.
It establishes only that the learned path is materially better than the deployed taste heuristic on the measured task.

## Gate Two: Learned Champion Selection

A challenger may replace hybrid through one of two predeclared routes.

### Quality Route

Use this route when the challenger has comparable or greater operational complexity than hybrid.

- NDCG@5 improves over hybrid by at least 0.02 absolute.
- The paired 95% confidence interval for NDCG@5 improvement over hybrid has a lower bound above zero.
- Pairwise preference accuracy does not regress.
- Known-dislike rate@5 does not regress by more than 0.01 absolute.
- Coverage does not fall below 0.98.

### Simplicity Route

Use this route only when the challenger materially reduces a cost declared before evaluation.

- The paired 95% confidence interval for challenger-minus-hybrid NDCG@5 has a lower bound no worse than -0.005.
- Pairwise preference accuracy and known-dislike safety do not regress beyond their locked guardrails.
- Coverage remains at least 0.98.
- At least one declared cost dimension improves by 25% or more.
- No other declared cost dimension worsens by more than 25% without founder approval.

Declared cost dimensions are training runtime, per-user scoring runtime, peak memory, artifact size, required feature-snapshot size, external data dependence, and operational services.
Qualitative complexity claims must be supported by a concrete dependency or operating-boundary change rather than preference alone.

The protocol does not collapse quality and cost into a post-hoc scalar utility score.
If neither route passes, hybrid remains champion even when the challenger beats V2.

## Metrics And Cohorts

The primary decision cohort is established users with 100 earlier ratings and 30 chronological future ratings.
NDCG@5 and pairwise preference accuracy remain co-primary quality metrics.
Known-dislike rate@5 remains the safety guardrail.
Coverage, per-user runtime, fitting runtime, peak memory, and artifact size remain mandatory.

Cold-start, deep-history, sparse-item, and prolific cohorts remain separate diagnostics.
A large subgroup improvement may motivate another candidate but cannot substitute for the primary established-user gate.
Every aggregate is per user and includes a paired 95% bootstrap confidence interval.

## Development Data Roles

The previous exploration, validation, and sealed MovieLens users are now retired from independent final-proof status.
Their 14,617 established users may be deterministically repartitioned into development roles because the original sealed result has already been opened.

- Development fit receives 8,770 users, approximately 60%.
- Development tune receives 2,923 users, approximately 20%.
- Internal test receives 2,924 users, approximately 20%.

This is not a reuse of the founder's earlier illustrative 60/40 suggestion.
The 2,924-user internal test is conservative relative to the paired uncertainty observed in the 5,000-user sealed run and is more than adequate to distinguish the locked 0.02 practical effect from zero at that observed variance scale.
The remaining allocation gives candidate fitting a larger population while retaining a separate 2,923-user tuning cohort.

The split is stratified by available cohort membership and generated from seed `20260711`.
One user has one development role across every cohort.
Fit labels may train model parameters.
Tune labels may select configurations within the predeclared search budget.
Internal-test labels remain unopened until each issue freezes its candidate configuration and may be opened once for the shared winner-selection packet.

The committed aggregate and checksum lock is `docs/validation/model-improvement-protocol-lock.json`.
The label-free local manifests verify with these SHA-256 checksums:

- Development fit: `7211a3380b298b037383d8d7a9d307707f2e6d2567c7c3406bb6c681d3115b7d`.
- Development tune: `7b4b35813464f31818d318be2cd42eb885e40d545d2a60ab3b477058db1f1f4d`.
- Internal test: `f2f7b58c3b4d53cb9a3691c1d2cdb3b5c4f7753076b2e2a7b7f777eb843c5b5f`.

Cross-role user overlap is zero.

The internal test is development evidence rather than a new independent final claim because aggregate results from the source population influenced this program.
Only issue #132 may create replacement sealed evidence from an independent source or newly approved eligibility contract.

## Candidate Search Budget

Issue #129 may evaluate at most 12 support-aware hybrid configurations on tune data.
Issue #130 may evaluate at most 12 ratings-only or ranking-oriented configurations on tune data.
Each issue freezes at most one candidate before the shared internal test.

The search budget prevents unlimited adaptation to the tune cohort.
A failed search is a valid result and does not require selecting a nominal winner.

## Versioned Data Inventory

| Data | Allowed role in this phase | Boundary |
| --- | --- | --- |
| Retired MovieLens ratings | Fit, tune, and internal development test | Individual historical taste only |
| MovieLens genres and release years | Fixed content snapshot | No live mutation |
| Exploration-cutoff MovieLens tags | Fixed content snapshot | No future tag leakage |
| MovieLens-to-TMDb links | Runtime identifier mapping | Contains no user evidence |
| TMDb cast, crew, language, and keywords | Not included in #129 or #130 | Requires a separate fixed-source and licensing slice |
| WatchSignal Taste Lab ratings | Product integration and future domain evaluation | Not mixed into MovieLens internal-test labels |
| Household selections and satisfaction | Future household-model evidence | Insufficient for training today |

Raw MovieLens rows remain local and ignored.
Committed reports contain aggregates, contracts, schemas, and checksums rather than user identifiers or histories.

## Experiment Record

Every candidate report records the code revision, data-manifest checksums, feature-snapshot checksum, configuration, seed, fit and tune runtime, peak memory, artifact checksum, candidate coverage, all locked metrics, exclusions, and failure reasons.
Training loss remains diagnostic and cannot select a recommendation model by itself.
The winner-selection packet must show V2, collaborative, hybrid, and every frozen challenger through the same evaluator.

## Replacement Sealed Trigger

Issue #132 remains blocked unless issue #131 freezes one challenger that clears learned eligibility and one champion-selection route on internal development evidence.
The replacement panel source, cohort rules, membership, and checksums must be approved before labels are opened.
The frozen winner runs exactly once against V2, collaborative, and hybrid.

Passing a replacement sealed gate identifies the offline quality champion.
Changing the WatchSignal product default remains a separate household decision when sufficient two-person evidence exists.

## Founder Decision

The founder approved the two-gate hypothesis:

- A learned model must substantially beat deployed V2 to qualify for product consideration.
- Among qualified learned models, additional quality must justify additional compute, data, and operational complexity.
- A simpler challenger may win by demonstrating near-equal quality and materially lower declared cost.
- Hybrid remains the quality champion until one of those routes passes.
- Household evidence may be collected later without blocking this offline discovery phase.
