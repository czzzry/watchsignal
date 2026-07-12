# MVP Plus 4 Recommendation Evaluation

Date: 2026-07-07

Phase: MVP+4: Recommendation Memory And Evaluation

Command: `pnpm eval:mvp4`

## Summary

- attribution_scenarios: 4
- attribution_passed: True
- recommendation_scenarios: 7
- recommendation_passed: 6
- recommendation_pass_rate: 0.8571
- known_gaps: ['named_actor_steer_surfaces_matching_cast']
- mvp_plus_4_evaluation_harness_passed: True

## Scenario Results

### profile_attribution_pairing_uses_both_household_profiles

- Category: attribution
- Passed: True
- Target: Arrival
- Top five before: Arrival, Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery, The Shining
- Top five after: Arrival, Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery, The Shining
- Expected movement: same
- Actual movement: same
- Target rank before: 1
- Target rank after: 1
- Before signals: genre, title_similarity, feature_tag
- After signals: genre, title_similarity, feature_tag
- Target enrichment provider after: fixed-mvp-plus-4-eval
- Target matched person names after: none
- Before explanation: Fits compromise mode with signal from Sci-Fi, Drama. Alex - tester: 0.66, Taste Lab signals: 1; Wife: 0.5, Taste Lab signals: 1. Evidence: genre, title_similarity, feature_tag.
- After explanation: Fits compromise mode with signal from Sci-Fi, Drama. Alex - tester: 0.66, Taste Lab signals: 1; Wife: 0.5, Taste Lab signals: 1. Evidence: genre, title_similarity, feature_tag.

### active_profile_taste_lab_isolation

- Category: attribution
- Passed: True
- Target: The Shining
- Top five before: Paddington 2, Dinner Party Mystery, Arrival, The Shining, Manchester by the Sea
- Top five after: The Shining, Mission: Impossible - Fallout, Arrival, Dinner Party Mystery, Manchester by the Sea
- Expected movement: up
- Actual movement: up
- Target rank before: 4
- Target rank after: 1
- Before signals: none
- After signals: genre, title_similarity
- Target enrichment provider after: fixed-mvp-plus-4-eval
- Target matched person names after: Jack Nicholson
- Before explanation: Strong fit for Wife with signal from Horror, Thriller. Built from profile score 0.5, 1 Taste Lab signals.
- After explanation: Strong fit for Alex - tester with signal from Horror, Thriller. Built from profile score 0.68, 1 Taste Lab signals. Evidence: genre, title_similarity.

### avoid_repeat_removes_already_watched_title

- Category: attribution
- Passed: True
- Target: Arrival
- Top five before: Arrival, Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery, The Shining
- Top five after: Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery, The Shining, Manchester by the Sea
- Expected movement: removed
- Actual movement: removed
- Target rank before: 1
- Target rank after: None
- Before signals: genre, title_similarity, feature_tag
- After signals: none
- Target enrichment provider after: fixed-mvp-plus-4-eval
- Target matched person names after: none
- Before explanation: Fits compromise mode with signal from Sci-Fi, Drama. Alex - tester: 0.66, Taste Lab signals: 1; Wife: 0.5, Taste Lab signals: 1. Evidence: genre, title_similarity, feature_tag.
- After explanation: None

### scary_steer_moves_horror_pick_up

- Category: recommendation
- Passed: True
- Target: The Shining
- Top five before: Arrival, Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery, The Shining
- Top five after: The Shining, Arrival, Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery
- Expected movement: up
- Actual movement: up
- Target rank before: 5
- Target rank after: 1
- Before signals: none
- After signals: tonight_intent
- Target enrichment provider after: fixed-mvp-plus-4-eval
- Target matched person names after: Jack Nicholson
- Before explanation: Fits compromise mode with signal from Horror, Thriller. Alex - tester: 0.5, Taste Lab signals: 1; Wife: 0.5, Taste Lab signals: 1.
- After explanation: Fits compromise mode with signal from Horror, Thriller. Alex - tester: 0.5, Taste Lab signals: 1; Wife: 0.5, Taste Lab signals: 1. Evidence: tonight_intent.

### sad_steer_moves_melancholy_drama_up

- Category: recommendation
- Passed: True
- Target: Manchester by the Sea
- Top five before: Arrival, Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery, The Shining
- Top five after: Manchester by the Sea, Arrival, Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery
- Expected movement: up
- Actual movement: up
- Target rank before: 6
- Target rank after: 1
- Before signals: none
- After signals: tonight_intent
- Target enrichment provider after: fixed-mvp-plus-4-eval
- Target matched person names after: none
- Before explanation: Fits compromise mode with signal from Drama. Alex - tester: 0.5, Taste Lab signals: 1; Wife: 0.5, Taste Lab signals: 1.
- After explanation: Fits compromise mode with signal from Drama. Alex - tester: 0.5, Taste Lab signals: 1; Wife: 0.5, Taste Lab signals: 1. Evidence: tonight_intent.

### named_actor_steer_surfaces_matching_cast

- Category: recommendation
- Passed: False
- Target: Mission: Impossible - Fallout
- Top five before: Arrival, Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery, The Shining
- Top five after: Arrival, Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery, The Shining
- Expected movement: up
- Actual movement: same
- Target rank before: 7
- Target rank after: 7
- Before signals: none
- After signals: none
- Target enrichment provider after: fixed-mvp-plus-4-eval
- Target matched person names after: Tom Cruise
- Before explanation: Fits compromise mode with signal from Action, Thriller. Alex - tester: 0.5, Taste Lab signals: 1; Wife: 0.5, Taste Lab signals: 1.
- After explanation: Fits compromise mode with signal from Action, Thriller. Alex - tester: 0.5, Taste Lab signals: 1; Wife: 0.5, Taste Lab signals: 1.

### comfort_movie_steer_moves_warm_comedy_up

- Category: recommendation
- Passed: True
- Target: Paddington 2
- Top five before: Arrival, Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery, The Shining
- Top five after: Paddington 2, Arrival, Edge of Tomorrow Again, Dinner Party Mystery, The Shining
- Expected movement: up
- Actual movement: up
- Target rank before: 2
- Target rank after: 1
- Before signals: genre, title_similarity, feature_tag
- After signals: genre, title_similarity, feature_tag, tonight_intent
- Target enrichment provider after: fixed-mvp-plus-4-eval
- Target matched person names after: none
- Before explanation: Fits compromise mode with signal from Comedy, Adventure. Alex - tester: 0.5, Taste Lab signals: 1; Wife: 0.62, Taste Lab signals: 1. Evidence: genre, title_similarity, feature_tag.
- After explanation: Fits compromise mode with signal from Comedy, Adventure. Alex - tester: 0.5, Taste Lab signals: 1; Wife: 0.62, Taste Lab signals: 1. Evidence: genre, title_similarity, feature_tag, tonight_intent.

### post_watch_no_moves_similar_title_down

- Category: recommendation
- Passed: True
- Target: Edge of Tomorrow Again
- Top five before: Edge of Tomorrow Again, Mission: Impossible - Fallout, Arrival, Dinner Party Mystery, The Shining
- Top five after: Mission: Impossible - Fallout, Arrival, Edge of Tomorrow Again, Dinner Party Mystery, The Shining
- Expected movement: down
- Actual movement: down
- Target rank before: 1
- Target rank after: 3
- Before signals: genre, title_similarity, feature_tag
- After signals: genre, title_similarity, feature_tag
- Target enrichment provider after: fixed-mvp-plus-4-eval
- Target matched person names after: none
- Before explanation: Strong fit for Action profile with signal from Action, Sci-Fi. Built from profile score 0.71, 1 Taste Lab signals. Evidence: genre, title_similarity, feature_tag.
- After explanation: Strong fit for Action profile with signal from Action, Sci-Fi. Built from profile score 0.52, 1 Taste Lab signals. Evidence: genre, title_similarity, feature_tag.

### watchlist_loved_moves_saved_style_up

- Category: recommendation
- Passed: True
- Target: Dinner Party Mystery
- Top five before: Arrival, Edge of Tomorrow Again, Dinner Party Mystery, The Shining, Manchester by the Sea
- Top five after: Dinner Party Mystery, Paddington 2, Arrival, The Shining, Manchester by the Sea
- Expected movement: up
- Actual movement: up
- Target rank before: 3
- Target rank after: 1
- Before signals: none
- After signals: genre, feature_tag
- Target enrichment provider after: fixed-mvp-plus-4-eval
- Target matched person names after: none
- Before explanation: Strong fit for Alex - tester with signal from Mystery, Comedy. Built from profile score 0.5, 1 Taste Lab signals.
- After explanation: Strong fit for Watchlist rater with signal from Mystery, Comedy. Built from profile score 0.66. Evidence: genre, feature_tag.

### partner_compromise_prefers_shared_fit_over_one_sided_pick

- Category: recommendation
- Passed: True
- Target: Dinner Party Mystery
- Top five before: Dinner Party Mystery, Paddington 2, Mission: Impossible - Fallout, Edge of Tomorrow Again, Arrival
- Top five after: Dinner Party Mystery, Paddington 2, Arrival, Manchester by the Sea, Past Lives
- Expected movement: shared fit stays first while one-sided action drops
- Actual movement: same
- Target rank before: 1
- Target rank after: 1
- Before signals: genre, feature_tag
- After signals: genre, feature_tag
- Target enrichment provider after: fixed-mvp-plus-4-eval
- Target matched person names after: none
- Before explanation: Fits husband-first mode with signal from Mystery, Comedy. Action and mystery: 0.66, Taste Lab signals: 2; Mystery fan: 0.66, Taste Lab signals: 2. Evidence: genre, feature_tag.
- After explanation: Fits compromise mode with signal from Mystery, Comedy. Action and mystery: 0.66, Taste Lab signals: 2; Mystery fan: 0.66, Taste Lab signals: 2. Evidence: genre, feature_tag.

### live_tmdb_candidate_shape_keeps_provider_evidence_visible

- Category: attribution
- Passed: True
- Target: Arrival
- Top five before: Arrival, Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery, The Shining
- Top five after: Arrival, Paddington 2, Edge of Tomorrow Again, Dinner Party Mystery, The Shining
- Expected movement: same
- Actual movement: same
- Target rank before: 1
- Target rank after: 1
- Before signals: genre, title_similarity, feature_tag
- After signals: genre, title_similarity, feature_tag, tonight_intent
- Target enrichment provider after: fixed-live-tmdb-eval
- Target matched person names after: none
- Before explanation: Fits compromise mode with signal from Sci-Fi, Drama. Alex - tester: 0.66, Taste Lab signals: 1; Wife: 0.5, Taste Lab signals: 1. Evidence: genre, title_similarity, feature_tag.
- After explanation: Fits compromise mode with signal from Sci-Fi, Drama. Alex - tester: 0.66, Taste Lab signals: 1; Wife: 0.5, Taste Lab signals: 1. Evidence: genre, title_similarity, feature_tag, tonight_intent.

## Caveats

- This is a deterministic local harness, not a live TMDb acceptance run.
- Recommendation scenarios use directional movement so useful tuning does not depend on exact ranks.
- Attribution scenarios are strict because profile ownership and repeat avoidance must not drift.
- Known recommendation gaps are reported without failing the command so later MVP+4 slices have a visible baseline.
