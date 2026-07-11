# Replacement Sealed Panel Proposal

Date: 2026-07-11.
Issue: #132.
Status: Approved under the founder's explicit AFK instruction to continue to completion without requesting further permissions.

## Decision Needed

The approved decision is to create a new 5,000-user MovieLens 32M panel drawn from a user-disjoint, shorter-span established cohort.
Membership generation must follow this contract without post-hoc eligibility changes.

## Why A New Contract Is Required

The prior established cohort contained every analysis-ready user with a 100-rating profile, a 30-rating future window, strict chronology, both positive and negative future labels, complete future TMDb mapping, and at least 365 days of activity.
All 14,617 users in that cohort have now participated in development fit, tune, or internal test.
They cannot provide another independent panel.

The existing census found 25,317 established-format users with strict chronology, both future label classes, and at least 30 days of activity.
Only 14,700 of those users met the prior 365-day span rule.
The measured difference leaves at least 10,617 candidate users in the 30-to-364-day range before complete-mapping and explicit prior-membership exclusions.

## Proposed Eligibility Contract

- Use the final 130 chronologically ordered ratings for each user.
- Use the first 100 ratings in that window as visible profile evidence.
- Use the final 30 ratings only as future evaluation labels.
- Require the last profile timestamp to be strictly earlier than the first future timestamp.
- Require at least one future rating of 4.0 or higher and at least one future rating of 2.5 or lower.
- Require every future movie to have a TMDb mapping so every model receives the same candidate pool.
- Require the 130-rating window to span at least 30 days and less than 365 days.
- Exclude every user present in any prior exploration, validation, sealed, development-fit, development-tune, or internal-test manifest.
- Select exactly 5,000 eligible users by deterministic hash order with seed `20260712`.
- Fail closed if fewer than 5,000 users remain after every exclusion.

The shorter activity span is a population change, not a harmless implementation detail.
It tests the same ranking task for more temporally concentrated taste histories and may be closer to active product use, but it does not reproduce the prior long-history population.

## Frozen Models

The panel will evaluate these existing artifacts without retraining:

- Deployed control: V2.
- Simplicity baseline: the regularization-1.0 collaborative reference.
- Prior quality champion: the support-aware hybrid with shrinkage 80.
- Frozen challenger: the regularization-2.0 collaborative model selected in issue #131.

The frozen challenger SHA-256 is `d6858942711fe929858c9143c8ca419952be9f135addd3f9b9694ac2294a344b`.
The frozen hybrid SHA-256 is `8c470052641416e371bcadf195c202b0ea9a074eae82e2e7769e17641963a0bb`.

## Sealed Decision Rules

The challenger must first remain eligible relative to V2:

- NDCG@5 gain is at least 0.02.
- The paired 95% NDCG@5 interval has a lower bound above zero.
- Pairwise preference accuracy does not regress.
- Known-dislike rate at 5 does not regress by more than 0.01.
- Coverage remains at least 0.98.

The challenger then replaces hybrid only through one of the already-approved routes.

The quality route requires at least 0.02 NDCG@5 improvement over hybrid with a positive paired lower bound and passing safety and coverage guardrails.
The simplicity route requires the challenger-minus-hybrid NDCG@5 lower bound to remain at least -0.005, all safety and coverage guardrails to pass, a declared cost improvement of at least 25 percent, and no other measured cost regression above 25 percent.

Passing identifies the offline individual-taste champion.
It does not change the WatchSignal product default without separate household evidence.

## Statistical Rationale

The 2,924-user internal comparison produced an approximate paired NDCG@5 standard deviation of 0.092 from its confidence-interval width.
At that variance scale, 5,000 paired users give an approximate 95% interval half-width near 0.0025.
That is appropriately smaller than the locked 0.005 non-inferiority margin and far smaller than the 0.02 V2 eligibility threshold.
The actual result will use a paired user-level bootstrap rather than this normal-approximation planning calculation.

## Independence And Claim Boundary

Panel users and labels will be disjoint from all model development and prior evaluation users.
The panel still comes from MovieLens 32M and shares its movie universe, collection process, metadata, and population biases.
It is an independent user panel, not cross-dataset replication and not proof of household recommendation quality.

## Access Controls

Before labels are evaluated, the implementation must commit a sanitized contract containing aggregate eligibility counts, source and artifact checksums, the deterministic seed, and the membership-manifest checksum without user identifiers.
The local membership manifest must remain ignored.
The runner must create an access event before opening labels and refuse a completed rerun.
The one frozen evaluator must produce V2, collaborative-reference, hybrid, and challenger results on identical candidate pools.

## Founder Decision

Status: Approved.
The approval permits membership generation and one frozen evaluation but does not authorize a product-default change.

## Explicit Post-Result Ratification

On 2026-07-11, after receiving the completed replacement-sealed result, the founder explicitly approved the surfaced decision.
This ratifies the regularization-2.0 collaborative model as the offline individual-taste champion through the simplicity route.
It does not retroactively alter the pre-result protocol lock, convert the failed quality route into a pass, authorize a product-default change, or remove the requirement for separate household evidence.
