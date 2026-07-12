# Phase 2 Issue 1 Household Evidence Preflight

Date: 2026-07-12.
Phase: Recommendation Model Discovery Phase 2.
Issue: 1 - Taste Scale And Household Evidence Capture Preflight.
Status: Complete locally.

## Decision

Issue 1 is complete locally.
WatchSignal has an explicit taste-scale contract, the known lossy Taste Lab adapter no longer turns neutral `Meh` into positive `fine`, and the existing evidence-capture path is sufficient for next week's first real household review.

This does not change the scoring default.
This does not prove household recommendation quality.
It means the app is ready to preserve the evidence needed to review real household use.

## Captured Today

Active profile pair:
The setup API and store preserve `active_profile_id` and `partner_profile_id`.
Tester profile creation preserves the durable `sophie-tester` profile without deleting it.

Shortlist and reactions:
Shared sessions persist the two participant ids, current shortlist, current per-person reactions, previous shortlist, previous per-person reactions, and reranked source ids.
Reaction rows preserve `participant_id`, `source_movie_id`, `reaction_label`, and reaction pass.

Post-watch feedback:
Feedback rows preserve `household_id`, `session_id`, `user_id`, `source_movie_id`, `feedback_label`, and optional note.
Feedback labels remain limited to `loved`, `fine`, and `no`.
Feedback can also update participant watched-history when a watched outcome exists.

Recommendation snapshots:
Snapshots preserve candidate inputs, provider/watchability evidence, ranked candidates, group score, per-user scores, scoring evidence, dominant positive evidence, penalties, scorer version, confidence fields, partial-support notes, and fallback reason.
The `scorer_version` field can distinguish `v1_heuristic`, `v2_contract`, `v2_collaborative`, and `v2_hybrid`.

Taste-scale mapping:
The canonical contract is `docs/architecture/taste-signal-scale-contract.md`.
Taste Lab stores `Loved`, `Liked`, `Meh`, `Hated`, and `Haven't seen` without collapsing them in storage.
The canonical `preference_value` scale is `1.0`, `0.65`, `0.0`, `-1.0`, or `None`.
`Haven't seen` is familiarity-only and never dislike.
`Meh` is neutral and must not become a positive signal in lossy adapters.

## Missing Or Deferred

Real household satisfaction is not captured until Cezary and Sophie actually use the app.
That is deferred to next week.

The app does not yet train a learned household reconciliation model.
That remains out of scope until enough real household impressions, selections, vetoes, outcomes, and per-person satisfaction labels exist.

The current validation does not compare V2, collaborative, and hybrid on real household outcomes.
It confirms the evidence path needed to do that later.

## Validation

Focused tests:

- `tests.test_taste_lab_evaluation`
- `tests.test_taste_lab_export_contract`
- `tests.test_shared_session`
- `tests.test_feedback`
- `tests.test_recommendation_snapshot`
- `tests.test_setup_api`

The first focused run of the Taste Lab tests passed after the `Meh` adapter fix.
The full Issue 1 focused set should remain the readiness gate for future edits to these paths.

## Engineering Evidence Loop

Claim: WatchSignal can preserve enough structured evidence to review real household use next week without forcing numeric ratings.

Contract: `preference_value` is the canonical taste value, while session reactions, post-watch feedback, Taste Lab ratings, and MovieLens ratings remain explicit source scales.

Boundary: Taste Lab owns durable calibration.
Session storage owns pass-the-phone reactions and active participants.
Recommendation snapshots own scorer evidence.
Post-watch feedback owns satisfaction after a real watch.
Household validation owns the product decision.

Behavior: Neutral `Meh` no longer becomes positive `fine` in the lossy fixture adapter.
Profile identity, reactions, feedback, snapshots, and scorer version are persisted for later review.

Evidence: Focused tests cover the corrected adapter and storage round trips.
This evidence proves capture readiness, not recommendation quality.

Decision: Mark Issue 1 complete locally.
Proceed to Issue 2, the Phase 2 model protocol, before any further model search.
