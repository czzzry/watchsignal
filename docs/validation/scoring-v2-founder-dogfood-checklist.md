# Scoring V2 Founder Dogfood Checklist

Date: 2026-07-09
Phase: Scoring V2: V2 Default Promotion Decision
Status: ready for founder dogfood

## Phase Tracker

```text
Scoring V2: [####################] 14/14 issues done
```

## Purpose

Use this checklist to decide whether V2 should become the default scorer, stay opt-in, or go through another revision loop.
The goal is not to prove the app works in general.
That has already passed locally.
The goal is to judge whether V2 feels better enough, trustworthy enough, and fast enough to become the default recommendation brain.

## Setup

Run the app with live TMDb.
V2 is now the default scorer:

```sh
MOVIE_NIGHT_RECOMMENDATION_SOURCE=live_tmdb pnpm --dir apps/web dev --hostname 127.0.0.1 --port 3000
```

To force the V1 rollback scorer during comparison testing, use:

```sh
MOVIE_NIGHT_RECOMMENDATION_SOURCE=live_tmdb MOVIE_NIGHT_SCORING_ENGINE=v1_heuristic pnpm --dir apps/web dev --hostname 127.0.0.1 --port 3000
```

Use a phone-sized browser viewport or open the local URL on a phone on the same network if available.
Keep the rollback command handy while doing this review.

## Review Flow

1. Start a normal couple session.
2. Keep Prime Germany selected.
3. Enter one ordinary night request you would actually use.
4. React through both passes without trying to game the system.
5. On results, inspect the winner, backups, explanation chips, held-back reasons, confidence, and any fallback notes.
6. Save an outcome and post-watch feedback.
7. Start a new night and confirm the profile ledger reflects the post-watch feedback.

## Suggested Prompts

Use one or two realistic prompts, not all of them in one pass:

- Something clever but not too heavy.
- No kids movies, no cartoonish stuff.
- Something cozy but not saccharine.
- More like Arrival but easier for a tired night.
- Something tense with a good cast.

## Scorecard

Rate each item from 1 to 5:

- Quality: the top pick feels better than the old app would have picked.
- Fit: the backups make sense as real alternatives.
- Trust: the explanation says something understandable and specific.
- Honesty: weak, partial, or fallback behavior is visible when appropriate.
- Speed: the flow feels couch-usable.
- Control: the nudge changes the direction without taking over the whole recommender.
- Profile learning: the app feels like it is using durable taste, not only tonight's text.

## Promotion Threshold

Promote V2 only if:

- Quality is at least 4.
- Trust is at least 4.
- Speed is at least 4.
- No pick feels obviously unsafe, unavailable, or against Prime Germany rules.
- At least one explanation makes you more confident in the recommendation.
- No issue requires changing the watchability, Prime Germany, or session-mode product rules.

## Rollback Threshold

Roll back to V1 default if:

- The picks are acceptable but not clearly better.
- The explanation is useful but not persuasive.
- You want more live nights before trusting V2 as default.
- You see taste-quality concerns but no urgent regression.

## Revise Threshold

Revise V2 before promotion if:

- The top pick is clearly wrong for the stated prompt.
- A disliked or avoided type rises too high.
- Repeated profile evidence seems ignored.
- Explanations feel generic, misleading, or too technical.
- The flow feels slow enough to interrupt the couch experience.

## Decision Prompt

After dogfood, choose one:

- Promote V2 to default.
- Roll back to V1 default and keep V2 available for revision.
- Revise V2 and repeat dogfood.

Record the decision in [docs/validation/scoring-v2-promotion-decision.md](scoring-v2-promotion-decision.md).
