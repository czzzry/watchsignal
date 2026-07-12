# Phase 2 Ranking-Oriented Collaborative Challenger

Date: 2026-07-12.
Phase: Recommendation Model Discovery Phase 2.
Issue: 4 - Train Ranking-Oriented Collaborative Challengers.
Status: Complete locally.

## Decision

Issue 4 is complete locally as a verified hold.
The existing bounded collaborative and ranking-oriented search already evaluated 12 predeclared ratings-only candidates and selected the regularization-2.0 collaborative model.
That selected model is now the current offline individual-taste champion.

Phase 2 does not freeze a new ratings-only challenger tonight.
Under the locked protocol, inventing another ratings-only search after seeing the replacement sealed result would require a new predeclared objective and candidate budget.

## Evidence

The existing search report is `docs/validation/movielens-collaborative-search.md`.
The selected candidate is `als_d16_r2_i5`.
The selected artifact SHA-256 is `d6858942711fe929858c9143c8ca419952be9f135addd3f9b9694ac2294a344b`.

The verification command rebuilt or checked the selected artifact and returned:

```text
expected: d6858942711fe929858c9143c8ca419952be9f135addd3f9b9694ac2294a344b
actual:   d6858942711fe929858c9143c8ca419952be9f135addd3f9b9694ac2294a344b
```

## Search Boundary

The prior search already included:

- Explicit ALS with multiple regularization values.
- Latent dimension changes.
- Iteration-count changes.
- Preference-weighted ALS variants that emphasize strong likes and dislikes.
- A 12-candidate declared budget.
- Tune-only selection with internal-test labels unopened at selection time.

The selected candidate later passed the replacement sealed simplicity route and became the offline champion.
That means Issue 4's strongest defensible local action is to verify the current champion rather than create a post-hoc ratings-only variant.

## Engineering Evidence Loop

Claim: The ratings-only collaborative lane does not currently have a new Phase 2 challenger that should displace the verified offline champion.

Contract: The selected collaborative artifact checksum must match the replacement sealed decision packet and runtime adapter expectation.

Boundary: Ratings-only collaborative search owns individual taste from historical ratings.
It must not use content metadata or real household usage.

Behavior: The selected artifact verifies exactly.
No new model is frozen.

Evidence: `pnpm eval:movielens:collaborative-search:verify` matched expected and actual SHA-256.

Decision: Mark Issue 4 complete locally as verified hold.
Proceed to Issue 5, the content-aware challenger lane, using only the Issue 3 approved feature families.
