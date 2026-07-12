# MVP Plus 3 Recommendation Quality

Date: 2026-07-07

Phase: MVP+3: Directed Discovery And Real Tester Profile

Target title: The Shining

## Summary

- baseline_top_pick: Cozy Mystery Night
- enriched_top_pick: The Shining
- enriched_target_rank_delta: 1
- top_pick_changed: True
- mvp_plus_3_recommendation_quality_passed: True

## Scenario Results

### baseline_no_profile_no_nudge

- Top pick: Cozy Mystery Night
- Target rank: 2
- Rank delta vs baseline: 0
- Top pick changed vs baseline: False
- Target signal families: none
- Matched person names: Jack Nicholson
- Top-pick explanation: Fits compromise mode with signal from Mystery, Comedy. Alex - tester: 0.5; Partner: 0.62, Taste Lab signals: 1. Evidence: genre.
- Target explanation: Fits compromise mode with signal from Horror, Thriller. Alex - tester: 0.5; Partner: 0.5, Taste Lab signals: 1.

### tester_profile_calibration

- Top pick: The Shining
- Target rank: 1
- Rank delta vs baseline: 1
- Top pick changed vs baseline: True
- Target signal families: genre, title_similarity
- Matched person names: Jack Nicholson
- Top-pick explanation: Fits compromise mode with signal from Horror, Thriller. Alex - tester: 0.92, Taste Lab signals: 3; Partner: 0.5, Taste Lab signals: 1. Evidence: genre, title_similarity.
- Target explanation: Fits compromise mode with signal from Horror, Thriller. Alex - tester: 0.92, Taste Lab signals: 3; Partner: 0.5, Taste Lab signals: 1. Evidence: genre, title_similarity.

### tester_profile_plus_directed_nudge

- Top pick: The Shining
- Target rank: 1
- Rank delta vs baseline: 1
- Top pick changed vs baseline: True
- Target signal families: genre, title_similarity, tonight_intent
- Matched person names: Jack Nicholson
- Top-pick explanation: Fits compromise mode with signal from Horror, Thriller. Alex - tester: 0.92, Taste Lab signals: 3; Partner: 0.5, Taste Lab signals: 1. Evidence: genre, title_similarity, tonight_intent.
- Target explanation: Fits compromise mode with signal from Horror, Thriller. Alex - tester: 0.92, Taste Lab signals: 3; Partner: 0.5, Taste Lab signals: 1. Evidence: genre, title_similarity, tonight_intent.

## Caveats

- The scenario is deterministic and local; it proves scoring movement, not live TMDb coverage.
- Named-person requests are represented in the shortlist payload and provider layer, while this scorer scenario uses the nudge text and matched-person evidence for review.
- Taste Lab evidence is deliberately visible in explanations so dogfood can judge whether calibration is helping.
- A broader recommendation evaluation corpus remains next-phase work.
