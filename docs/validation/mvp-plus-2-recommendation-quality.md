# MVP Plus 2 Recommendation Quality Report

Generated: 2026-07-02

## Summary

- Baseline top pick: Dinner Party Mystery
- Enriched top pick: Edge of Tomorrow Again
- Enriched target rank delta: 1
- Enrichment rate: 0.5
- Recommendation-quality passed: True

## Scenarios

### baseline_genre_only

- Top pick: Dinner Party Mystery
- Target rank: 2
- Rank delta vs baseline: 0
- Top pick changed vs baseline: False
- Enrichment coverage: 0/4 enriched, 4 fallback, rate 0.0
- Top pick signal families: fallback
- Top pick explanation: Fits compromise mode with signal from Mystery, Comedy. Founder: 0.5. Evidence: fallback.

### fallback_rich_profile

- Top pick: Edge of Tomorrow Again
- Target rank: 1
- Rank delta vs baseline: 1
- Top pick changed vs baseline: True
- Enrichment coverage: 0/4 enriched, 4 fallback, rate 0.0
- Top pick signal families: genre, title_similarity, fallback
- Top pick explanation: Fits compromise mode with signal from Action, Sci-Fi. Founder: 0.88, Taste Lab signals: 1. Evidence: genre, title_similarity, fallback.

### enriched_rich_profile_intent_reactions

- Top pick: Edge of Tomorrow Again
- Target rank: 1
- Rank delta vs baseline: 1
- Top pick changed vs baseline: True
- Enrichment coverage: 2/4 enriched, 2 fallback, rate 0.5
- Top pick signal families: genre, title_similarity, feature_tag, tonight_intent, session_reaction
- Top pick explanation: Fits compromise mode with signal from Action, Sci-Fi. Founder: 1.0, Taste Lab signals: 1. Evidence: genre, title_similarity, feature_tag, tonight_intent, session_reaction.

## Risk Notes

- Coverage is mixed by design, so fallback behavior remains visible.
- The enriched scenario improves the fixed target rank without requiring every candidate to be mapped.
- Weights are intentionally modest and should be retuned against broader household feedback before production claims.
- Title similarity is useful for reviewable movement but can overfit sequels or remakes if used without collision checks.
