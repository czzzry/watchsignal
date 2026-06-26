# Scoring Module Contract

This file defines the MVP scoring-module seam.
The scoring module should remain replaceable.
The first implementation can be simple.
The interface should still support later sophistication upgrades.

## Purpose

The scoring module receives:

- session context
- household defaults
- user taste signals
- candidate metadata

It returns:

- per-user scores
- group or session-mode-aware scores
- ranking order
- short explanation hints

The scoring module should not own:

- Telegram messaging
- Google Sheets persistence
- n8n workflow orchestration
- credential handling

## Input contract

```json
{
  "session": {
    "session_id": "string",
    "requested_media_type": "movie|tv",
    "audience_mode": "solo|shared",
    "session_mode": "husband_first|wife_first|compromise",
    "mood_text": "string|null",
    "runtime_pref": "string|null",
    "genre_hint": "string|null",
    "region": "string|null",
    "service_constraint": "string|null",
    "language_constraint": "string|null"
  },
  "household_defaults": {
    "default_service": "string|null",
    "default_language_mode": "string|null",
    "rewatch_avoidance_default": true
  },
  "users": [
    {
      "user_id": "string",
      "role": "user_a|user_b|solo",
      "seed_summary": {
        "liked_titles": ["string"],
        "fine_titles": ["string"],
        "disliked_titles": ["string"]
      },
      "hard_constraints": {
        "subtitle_intolerance": false,
        "horror_exclusion": false
      }
    }
  ],
  "candidates": [
    {
      "source_movie_id": "string",
      "title": "string",
      "media_type": "movie|tv",
      "release_year": 2024,
      "runtime_min": 110,
      "genres": ["Action", "Thriller"],
      "overview": "string",
      "providers": ["Prime Video"],
      "language_metadata": {
        "original_language": "en",
        "spoken_languages": ["en"]
      },
      "already_watched": false
    }
  ]
}
```

## Output contract

```json
{
  "session_id": "string",
  "ranked_candidates": [
    {
      "source_movie_id": "string",
      "candidate_rank": 1,
      "fit_bucket": "user_a|user_b|compromise|shared",
      "user_a_score": 0.83,
      "user_b_score": 0.64,
      "group_score": 0.79,
      "why_short": "Fits tonight's mode and your strong overlap on spy thrillers.",
      "hard_filter_pass": true
    }
  ],
  "uncertainty": {
    "is_uncertain": false,
    "reason": null,
    "recommended_follow_up": null
  }
}
```

## MVP behavior expectations

- Honor hard constraints first
- Exclude already watched titles by default unless the session allows rewatches
- Produce per-user scores separately
- Produce a mode-aware group score
- Return a concise `why_short` hint per candidate
- Signal uncertainty when the model lacks enough confidence

## V1 heuristic scoring direction

The first real scorer should be taste-aware, but still intentionally simple and inspectable.
It is not meant to be the final recommender.

V1 should move beyond popularity-only ranking by combining:

- hard-filter passes for language, rewatch posture, and other explicit constraints
- positive signal from titles the user loved
- softer positive signal from titles the user marked fine
- penalty signal from titles the user disliked
- signal from real watched outcomes and post-watch feedback
- session-context fit such as solo mode and requested media type

Useful early features can include:

- genre overlap with liked titles
- genre penalties from disliked titles
- cast or crew recurrence when metadata is available
- simple keyword or overview overlap when available
- preference for titles that fit explicit household defaults

V1 should avoid pretending to infer very deep taste patterns that the data cannot yet support.
Its job is to be a credible first brain, not a magical final one.

## What is durable vs temporary

Likely durable:

- the scoring seam itself
- hard constraints before ranking
- separate per-user scoring
- structured use of onboarding seeds and real feedback
- storing explanation hints in the ranking output

Likely temporary:

- exact weight choices
- popularity-heavy fallback behavior
- simplistic overlap heuristics
- generic explanation text

## LLM evolution posture

The mature product may use LLM assistance heavily for interpretation and enrichment.
That does not mean the MVP scorer is wasted work.

Expected later LLM contributions:

- interpret free-text notes into softer taste signals
- summarize recurring themes or aversions
- enrich explanation quality
- help surface less obvious cross-title connections

The preferred long-term architecture is hybrid:

- deterministic filtering and structured scoring as the recommendation backbone
- LLM-assisted enrichment layered on top

The MVP scorer should therefore be built as a replaceable heuristic scoring module, not as the final recommendation ideology.

## Non-goals for MVP

- LLM ranking authority
- Deep model training
- Embeddings-first ranking
- Full recommendation explainability
- Provider-specific audio-track verification

## Upgrade expectations

- MVP plus 1 may enrich taste interpretation from free text
- The internal scoring method may change without changing this seam materially
- The scoring module may later live outside n8n while preserving the same contract shape
