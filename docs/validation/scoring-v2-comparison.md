# Scoring V2 Comparison

Date: 2026-07-09
Phase: Scoring V2: V1 And V2 Corpus Comparison
Command: `pnpm eval:scoring-v2:compare`

## Summary

- Scenario count: 7
- V2 improvements: 1
- Unchanged scenarios: 6
- Regressions: 0
- V2 scorer version: v2_contract

## Scenario Results

### negative_kid_animation_request

- Category: negative_preference
- Expected behavior: Adult mystery should rank above family animation.
- V2 status: unchanged
- V1 top five: Knives Out, Paddington, Spider-Man: Into the Spider-Verse
- V2 top five: Knives Out, Paddington, Spider-Man: Into the Spider-Verse
- V1 preferred rank: 1
- V2 preferred rank: 1
- V1 avoided rank: 3
- V2 avoided rank: 3
- V2 confidence: high (1.0)
- V2 fallback: none
- V2 positive evidence: concept:mystery, concept:procedural, concept:witty, profile_concept:likes:mystery, memory_source:taste_lab:mystery, profile_concept:likes:procedural, memory_source:taste_lab:procedural, metadata:concepts, metadata:feature_tags, metadata:overview_themes, metadata:runtime, metadata:language, title_similarity:Knives Out, genre:Mystery, genre:Comedy
- V2 penalties: none

### actor_driven_josh_brolin_request

- Category: actor_driven
- Expected behavior: A Josh Brolin match should outrank a generic action title.
- V2 status: unchanged
- V1 top five: Sicario, Generic Siege
- V2 top five: Sicario, Generic Siege
- V1 preferred rank: 1
- V2 preferred rank: 1
- V1 avoided rank: 2
- V2 avoided rank: 2
- V2 confidence: low (0.44)
- V2 fallback: top_candidate_uses_metadata_fallback
- V2 positive evidence: concept:tense, concept:procedural, profile_concept:likes:tense, memory_source:taste_lab:tense, metadata:concepts, metadata:overview_themes, metadata:cast, metadata:runtime, metadata:language, genre:Thriller, tonight_intent:tense
- V2 penalties: metadata:fallback

### subtle_tone_cozy_not_saccharine

- Category: subtle_tone
- Expected behavior: A warm grown-up comedy should beat a sweeter family pick.
- V2 status: unchanged
- V1 top five: The Grand Budapest Hotel, Paddington
- V2 top five: The Grand Budapest Hotel, Paddington
- V1 preferred rank: 1
- V2 preferred rank: 1
- V1 avoided rank: 2
- V2 avoided rank: 2
- V2 confidence: high (0.937365)
- V2 fallback: none
- V2 positive evidence: concept:cozy, concept:witty, profile_concept:likes:witty, memory_source:taste_lab:witty, metadata:concepts, metadata:feature_tags, metadata:overview_themes, metadata:runtime, metadata:language, title_similarity:The Grand Budapest Hotel, genre:Comedy, tonight_intent:cozy
- V2 penalties: none

### high_confidence_solo_favorite

- Category: solo_favorite
- Expected behavior: Arrival should rank first for a cerebral first-contact profile.
- V2 status: unchanged
- V1 top five: Arrival, Quiet Legal Drama, Reflective Romance, Loud Space Battle, Witty Mystery
- V2 top five: Arrival, Loud Space Battle, Reflective Romance, Quiet Legal Drama, Witty Mystery
- V1 preferred rank: 1
- V2 preferred rank: 1
- V1 avoided rank: 4
- V2 avoided rank: 2
- V2 confidence: high (1.0)
- V2 fallback: none
- V2 positive evidence: concept:first-contact, concept:cerebral, profile_concept:likes:cerebral, memory_source:post_watch_feedback:cerebral, profile_concept:likes:first-contact, memory_source:post_watch_feedback:first-contact, metadata:concepts, metadata:feature_tags, metadata:overview_themes, metadata:runtime, metadata:language, genre:Sci-Fi, genre:Drama, title_similarity:Arrival
- V2 penalties: none

### repeated_mismatch_suppression

- Category: mismatch_suppression
- Expected behavior: Shared comedy should beat one-sided action after repeated no signals.
- V2 status: unchanged
- V1 top five: Shared Laugh, One-Sided Action
- V2 top five: Shared Laugh, One-Sided Action
- V1 preferred rank: 1
- V2 preferred rank: 1
- V1 avoided rank: 2
- V2 avoided rank: 2
- V2 confidence: low (0.44)
- V2 fallback: top_candidate_uses_metadata_fallback
- V2 positive evidence: concept:witty, profile_concept:likes:witty, memory_source:taste_lab:witty, shared_fit:user_a:0.53, shared_fit:user_b:0.55, shared:overlap_strength, shared:bridge_value, genre:Comedy
- V2 penalties: none

### household_bridge_pick

- Category: household_bridge
- Expected behavior: A cerebral mystery bridge should beat one-sided favorites.
- V2 status: unchanged
- V1 top five: Arrival, Pure Romance Night, Pure Action Night
- V2 top five: Arrival, Pure Romance Night, Pure Action Night
- V1 preferred rank: 1
- V2 preferred rank: 1
- V1 avoided rank: 3
- V2 avoided rank: 3
- V2 confidence: high (1.0)
- V2 fallback: none
- V2 positive evidence: concept:first-contact, concept:cerebral, profile_concept:likes:cerebral, memory_source:taste_lab:cerebral, profile_concept:likes:first-contact, memory_source:taste_lab:first-contact, shared_fit:user_a:0.66, shared_fit:user_b:0.55, shared:overlap_strength, shared:bridge_value, genre:Sci-Fi, genre:Drama, genre:Mystery
- V2 penalties: none

### legitimate_no_strong_match

- Category: no_strong_match
- Expected behavior: The scorer should be uncertain or explicitly say no strong match.
- V2 status: improved
- V1 top five: Foreign Musical, Long Legal Drama
- V2 top five: Foreign Musical, Long Legal Drama
- V1 preferred rank: None
- V2 preferred rank: None
- V1 avoided rank: None
- V2 avoided rank: None
- V2 confidence: low (0.25)
- V2 fallback: top_candidate_uses_metadata_fallback
- V2 positive evidence: concept:reflective, metadata:concepts, metadata:runtime, metadata:language, tonight_intent:musical
- V2 penalties: metadata:fallback

## Risk Notes

- This is a deterministic fixture comparison, not a replacement for founder dogfood.
- V2 is now the default scorer after the founder promotion decision.
- V1 remains available as the rollback scorer.
- Live TMDb quality depends on provider candidate supply as well as scorer behavior.
