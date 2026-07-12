# Phase 2 Final Decision

Date: 2026-07-12.
Phase: Recommendation Model Discovery Phase 2.
Issue: 8 - Run The Fresh Evidence Gate And Record The Decision.
Status: Complete locally.

## Decision

The Phase 2 final decision is `hold_current_offline_champion`.

The collaborative regularization-2.0 model remains the offline individual-taste champion.
The support-aware hybrid remains the complexity comparator.
V2 remains the product default.
No fresh evidence panel was created or spent.
No labels were opened.
No product-default change was made.

## Why No Fresh Gate Ran

Issue 8 is designed to run a frozen Phase 2 candidate exactly once against approved fresh evidence.
Issue 6 selected no new challenger.
Issue 7 therefore decided not to spend fresh evidence.

With no frozen candidate and no approved fresh panel, a benchmark run would be fake ceremony rather than science.
The right scientific decision is to stop the Phase 2 model-discovery lane here and preserve the current evidence boundary.

## What Phase 2 Actually Achieved

Phase 2 did not produce a better model.
It did produce a cleaner operating posture:

- The rating-scale mismatch was fixed where `Meh` could become positive `fine`.
- The canonical taste-scale contract now separates user-friendly UI labels from internal preference values.
- The household evidence-capture path is ready for real use next week.
- The model protocol now separates deployed control, offline champion, complexity comparator, challenger, and fresh-evidence rules.
- The feature inventory prevents live mutable TMDb metadata from entering training without a fixed-source contract.
- The collaborative champion and support-aware hybrid artifacts were both reverified by checksum.
- Fresh evidence was preserved because there was no new challenger worth testing.

## Current Model State

| Role | Model | Status |
| --- | --- | --- |
| Product default | V2 | Unchanged |
| Offline individual-taste champion | Collaborative regularization 2.0 | Retained |
| Complexity comparator | Support-aware hybrid | Retained |
| Phase 2 challenger | None | No candidate frozen |
| Household model | None | Not trained |

## Next Real Work

The strongest next product work is real household validation after release.
That means using WatchSignal with Cezary and Sophie, preserving shortlist reactions, final choice, and post-watch satisfaction, then reviewing whether recommendations feel fair and useful.

The strongest next model-research work is a separate fixed-source metadata slice.
That slice would decide whether to create a local, dated, license-reviewed snapshot for cast, director, writer, keywords, runtime, language, collections, and production data.
Only after that snapshot exists should a new richer content-aware challenger be trained.

## Engineering Evidence Loop

Claim: Phase 2 should hold the current offline champion rather than force a new model or spend fresh evidence.

Contract: A fresh-evidence gate requires one frozen challenger and an approved evidence panel.

Boundary: Offline model discovery cannot prove household product quality.
Household validation remains separate.

Behavior: No fresh benchmark runs.
No product default changes.
No sealed or fresh labels opened.

Evidence: Issues 1 through 7 completed locally, verified artifacts, and recorded no new frozen challenger.

Decision: Mark Phase 2 complete at 8/8 with hold decision.
Recommended next phase is household dogfood validation and optional fixed-source metadata scoping.
