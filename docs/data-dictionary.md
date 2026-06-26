# Data Dictionary

This is the working MVP data dictionary for Slice 2.
It defines the first operating model for the product.
It is intentionally spreadsheet-friendly and portable to a later SQL-backed design.
It is not a final long-term schema.

## Design principles

- Keep the MVP portable across spreadsheet tabs and a future SQL database
- Store only the minimum private data needed to operate the product
- Separate raw inputs from derived scores and explanations
- Keep n8n orchestration state inspectable in Google Sheets
- Preserve enough session artifacts to measure improvement over time

## Google Sheets tab plan

The first operating store should use these tabs:

- `households`
- `users`
- `onboarding_seeds`
- `sessions`
- `session_candidates`
- `shortlist_reactions`
- `outcomes`
- `post_watch_feedback`
- `watched_history`
- `metrics_events`

## Working entities

### `households`

Represents the household or decision group.

Working fields:
- `household_id`
- `label`
- `default_region`
- `default_service`
- `default_language_mode`
- `rewatch_avoidance_default`
- `active_interface`
- `created_at`

### `users`

Represents each participant in the household.

Working fields:
- `user_id`
- `household_id`
- `display_label`
- `chat_platform`
- `chat_user_ref`
- `separate_device_enabled`
- `onboarding_completed_at`
- `created_at`

### `onboarding_seeds`

Represents seed titles and onboarding signals captured before real recommendations.

Working fields:
- `seed_id`
- `user_id`
- `source_movie_id`
- `media_type`
- `seed_label`
- `notes`
- `captured_at`

`seed_label` should start with:
- `loved`
- `fine`
- `no`

### `sessions`

Represents a single movie-night decision cycle.

Working fields:
- `session_id`
- `household_id`
- `initiator_user_id`
- `started_at`
- `status`
- `requested_media_type`
- `audience_mode`
- `session_mode`
- `mood_text`
- `runtime_pref`
- `genre_hint`
- `region`
- `service_constraint`
- `language_constraint`
- `uncertainty_reason`
- `resumable_until`

### `session_candidates`

Represents candidate titles considered within a session.

Working fields:
- `candidate_id`
- `session_id`
- `source_movie_id`
- `title`
- `media_type`
- `candidate_rank`
- `hard_filter_pass`
- `fit_bucket`
- `user_a_score`
- `user_b_score`
- `group_score`
- `why_short`
- `providers_snapshot`

`fit_bucket` should start with:
- `user_a`
- `user_b`
- `compromise`
- `shared`

### `shortlist_reactions`

Represents pre-watch reactions to shortlist items.

Working fields:
- `reaction_id`
- `session_id`
- `user_id`
- `source_movie_id`
- `reaction_label`
- `already_seen_flag`
- `reacted_at`

`reaction_label` should start with:
- `interested`
- `maybe`
- `no`
- blank for skipped items

### `outcomes`

Represents what actually happened after the session.

Working fields:
- `outcome_id`
- `session_id`
- `outcome_type`
- `selected_source_movie_id`
- `selected_title`
- `selection_origin`
- `recorded_at`
- `notes`

`outcome_type` should start with:
- `watched_recommended`
- `watched_other`
- `watched_nothing`

`selection_origin` should start with:
- `pick_for_us`
- `reranked_shortlist`
- `manual_other_choice`

### `post_watch_feedback`

Represents per-person feedback after a movie or show was watched.

Working fields:
- `feedback_id`
- `session_id`
- `user_id`
- `source_movie_id`
- `feedback_label`
- `free_text_note`
- `recorded_at`

`feedback_label` should start with:
- `loved`
- `fine`
- `no`

### `watched_history`

Represents the known watched-state for users and the household.

Working fields:
- `history_id`
- `household_id`
- `user_id`
- `source_movie_id`
- `title`
- `media_type`
- `watched_flag`
- `last_feedback_label`
- `source_of_truth`
- `updated_at`

`source_of_truth` should start with:
- `onboarding`
- `manual_backfill`
- `already_seen_correction`
- `post_watch_outcome`

### `audit_events`

Represents key system events needed for debugging or explanation.

Working fields:
- `event_id`
- `session_id`
- `event_type`
- `payload_json`
- `created_at`

This can be deferred if `metrics_events` is enough for MVP.

### `metrics_events`

Represents the measurable product events used to judge improvement.

Working fields:
- `metric_event_id`
- `session_id`
- `user_id`
- `event_type`
- `event_value`
- `recorded_at`

`event_type` should start with:
- `session_started`
- `shortlist_presented`
- `shortlist_rated`
- `pick_for_us_used`
- `refine_search_used`
- `start_over_used`
- `watched_recommended`
- `watched_other`
- `watched_nothing`
- `post_watch_feedback_recorded`
- `uncertainty_triggered`

## Privacy notes

- `chat_user_ref` should be treated as private operational data
- `free_text_note` and `notes` should stay optional and should not contain raw household chat exports
- Public examples must use synthetic values only
- Secrets and credentials do not belong in Sheets
