# MVP Plus 2 Contracts

This note defines the first shared contract surface for MVP Plus 2.
The goal is to let profile, watchlist, intent, continuation, enrichment, scoring, and evaluation work proceed in parallel without inventing incompatible shapes.

MVP Plus 2 is **Memory, Steering, And Rich Recommendation Intelligence**.
The locked tracker is [#48 through #59](../issues/mvp-plus-2-issue-breakdown.md).

## Contract Principles

- TMDb remains the live candidate and display source.
- MovieLens Tag Genome or derived offline features enrich candidates when a reliable mapping exists.
- Fallback candidates are allowed when enrichment is missing.
- LLMs interpret human intent into structured filters and soft signals.
- LLMs do not rank movies.
- Saved-for-later is shared household memory, not an automatic taste vote.
- Taste Lab remains outside the visible main app flow, but its backend evidence can still feed profile evidence.
- Show 5 more and Steer next 5 continue tonight's context instead of resetting it.

## Profile Identity

Profile identity includes:

- `profile_id`
- `display_label`
- `avatar_key`
- `color_key`

MVP Plus 2 supports labels and lightweight avatars or colors.
It does not support photo upload.
It does not redesign onboarding.

## Shared Watchlist

Watchlist entries include:

- `household_id`
- `source_movie_id`
- `title`
- `saved_at`
- optional `saved_by_profile_id`
- optional poster and release metadata

The visible list is shared by default.
The optional saved-by profile is provenance for later behavior.
It is not a scoring boost in MVP Plus 2.

## Tonight Intent

Tonight intent interpretation has two states:

- `confirmation_required`
- `clarification_required`

Concrete requests should return structured filters, soft signals, confidence, and confirmation text.
Ambiguous emotional requests should return one short clarification question.
Examples:

- "something from the 90s" maps to a year filter.
- "a Mel Gibson movie I haven't seen" maps to person and rewatch filters.
- "ugh, I feel sad today" asks whether the user wants to match the mood or be cheered up.

The app applies intent only after confirmation.

## Session Continuation

Continuation has two kinds:

- `show_more`
- `steer_next`

Show 5 more keeps prior reactions, active intent, and already-shown exclusions.
Steer next 5 requires a new steer text, runs through the same intent contract, and then continues with prior context plus the confirmed steer.

## Candidate Enrichment

Candidate enrichment has two states:

- `enriched`
- `fallback`

Enriched candidates have a matched offline source movie id and feature scores.
Fallback candidates remain rankable with TMDb metadata and existing scorer inputs.

Coverage must be tracked because MVP Plus 2 is only meaningful if the richer engine is actually being used.
The first implementation note is [Candidate Enrichment Pipeline](candidate-enrichment-pipeline.md).

## Scoring Evidence

Scoring evidence should identify signal families such as:

- `genre`
- `title_similarity`
- `feature_tag`
- `session_reaction`
- `tonight_intent`
- `fallback`

Future scoring work can add weights and richer internals, but the evidence surface should preserve which family moved the pick.

## Evaluation Coverage

The acceptance report should include:

- scenario name
- candidate count
- enriched candidate count
- fallback candidate count
- enrichment rate
- rank deltas
- top-pick changes
- explanation excerpts

MVP Plus 2 is not done until the phone-sized flow and recommendation-quality report both pass.
