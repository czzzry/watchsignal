# Phase 2 Content-Aware Challenger

Date: 2026-07-12.
Phase: Recommendation Model Discovery Phase 2.
Issue: 5 - Train Richer Content-Aware Challengers.
Status: Complete locally.

## Decision

Issue 5 is complete locally as a verified hold.
The approved Phase 2 feature inventory allows only fixed MovieLens genre, era, and authorized tag features.
The existing support-aware hybrid already uses those eligible feature families and remains the bounded content-aware comparator.

Phase 2 does not train a new richer content-aware challenger tonight.
Training on TMDb cast, director, writer, language, runtime, keywords, collections, production country, or production-company features would violate the Issue 3 inventory unless a separate fixed-source metadata snapshot is created first.

## Evidence

The support-aware hybrid report is `docs/validation/movielens-support-aware-hybrid.md`.
The selected artifact SHA-256 is `8c470052641416e371bcadf195c202b0ea9a074eae82e2e7769e17641963a0bb`.

The verification command returned:

```text
expected: 8c470052641416e371bcadf195c202b0ea9a074eae82e2e7769e17641963a0bb
actual:   8c470052641416e371bcadf195c202b0ea9a074eae82e2e7769e17641963a0bb
```

## Feature Boundary

Eligible content families:

- Genre.
- Era.
- Authorized MovieLens tags.

Excluded from Phase 2 training:

- Cast.
- Director.
- Writer.
- Language.
- Runtime.
- Keywords.
- Collections.
- Production country.
- Production company.
- Any live TMDb field without a fixed local snapshot and license review.

## Interpretation

The support-aware hybrid is a serious content-aware model, but it did not earn replacement over collaborative in the prior sealed decision.
It remains useful as the complexity comparator.
It should not be expanded with live mutable metadata in this phase just because those fields feel intuitively promising.

## Engineering Evidence Loop

Claim: The approved Phase 2 content-aware lane has no new eligible feature families beyond the already verified support-aware hybrid.

Contract: Issue 5 candidates must use the Issue 3 approved feature inventory and fixed snapshots.

Boundary: Runtime product metadata can support filtering and explanations.
Offline content-aware model training can use only fixed, approved training features.

Behavior: The support-aware hybrid artifact verifies exactly.
No new content-aware challenger is frozen.

Evidence: `pnpm eval:movielens:support-aware:verify` matched expected and actual SHA-256.

Decision: Mark Issue 5 complete locally as verified hold.
Proceed to Issue 6 selection, where the verified collaborative champion and verified support-aware hybrid should produce a hold rather than a new winner.
