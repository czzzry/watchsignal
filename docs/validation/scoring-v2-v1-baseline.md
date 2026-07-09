# Scoring V2 V1 Baseline

Date: 2026-07-09
Phase: Scoring V2: Evaluation Corpus And V1 Baseline
Command: `pnpm eval:scoring-v2:v1`

## Summary

- Scenario count: 7
- Harness passed: True
- V1 successes: 0
- V1 partials: 7
- V1 misses: 0

## Scenario Results

### negative_kid_animation_request

- Category: negative_preference
- User story: As a user, I can say no kids movies and no cartoonish stuff.
- Expected behavior: Adult mystery should rank above family animation.
- Top five: Knives Out, Paddington, Spider-Man: Into the Spider-Verse
- Preferred: Knives Out at rank 1
- Avoided: Spider-Man: Into the Spider-Verse at rank 3
- Signal families: genre, title_similarity, feature_tag
- Concept hits: whodunit, witty
- Penalty hits: none
- V1 status: partial
- V2 gap: V2 should improve penalties: animation, family, kids.

### actor_driven_josh_brolin_request

- Category: actor_driven
- User story: As a user, I can ask for a named actor and have that matter.
- Expected behavior: A Josh Brolin match should outrank a generic action title.
- Top five: Sicario, Generic Siege
- Preferred: Sicario at rank 1
- Avoided: Generic Siege at rank 2
- Signal families: genre, tonight_intent, fallback
- Concept hits: none
- Penalty hits: none
- V1 status: partial
- V2 gap: V2 should improve positive concepts: Josh Brolin, person.

### subtle_tone_cozy_not_saccharine

- Category: subtle_tone
- User story: As a user, I can ask for cozy but not saccharine.
- Expected behavior: A warm grown-up comedy should beat a sweeter family pick.
- Top five: The Grand Budapest Hotel, Paddington
- Preferred: The Grand Budapest Hotel at rank 1
- Avoided: Paddington at rank 2
- Signal families: genre, title_similarity, feature_tag, tonight_intent
- Concept hits: cozy, witty
- Penalty hits: none
- V1 status: partial
- V2 gap: V2 should improve penalties: saccharine, family.

### high_confidence_solo_favorite

- Category: solo_favorite
- User story: As a solo user, strong repeated evidence should produce a confident favorite.
- Expected behavior: Arrival should rank first for a cerebral first-contact profile.
- Top five: Arrival, Quiet Legal Drama, Reflective Romance, Loud Space Battle, Witty Mystery
- Preferred: Arrival at rank 1
- Avoided: Loud Space Battle at rank 4
- Signal families: genre, title_similarity, feature_tag
- Concept hits: cerebral, first-contact
- Penalty hits: none
- V1 status: partial
- V2 gap: V2 should improve positive concepts: Taste Lab.

### repeated_mismatch_suppression

- Category: mismatch_suppression
- User story: As a couple, repeated bad fits should stop resurfacing.
- Expected behavior: Shared comedy should beat one-sided action after repeated no signals.
- Top five: Shared Laugh, One-Sided Action
- Preferred: Shared Laugh at rank 1
- Avoided: One-Sided Action at rank 2
- Signal families: genre, fallback
- Concept hits: comedy
- Penalty hits: none
- V1 status: partial
- V2 gap: V2 should improve positive concepts: shared; penalties: repeated mismatch, action.

### household_bridge_pick

- Category: household_bridge
- User story: As a couple, we can get a bridge pick instead of a bland middle.
- Expected behavior: A cerebral mystery bridge should beat one-sided favorites.
- Top five: Arrival, Pure Romance Night, Pure Action Night
- Preferred: Arrival at rank 1
- Avoided: Pure Action Night at rank 3
- Signal families: genre, feature_tag
- Concept hits: cerebral, mystery
- Penalty hits: none
- V1 status: partial
- V2 gap: V2 should improve positive concepts: bridge, overlap; penalties: veto risk.

### legitimate_no_strong_match

- Category: no_strong_match
- User story: As a user, I get an honest no-strong-match state when the request is over-constrained.
- Expected behavior: The scorer should be uncertain or explicitly say no strong match.
- Top five: Foreign Musical, Long Legal Drama
- Preferred: None at rank None
- Avoided: None at rank None
- Signal families: tonight_intent, fallback
- Concept hits: none
- Penalty hits: none
- V1 status: partial
- V2 gap: V2 should improve positive concepts: courtroom, cozy, short runtime; penalties: over constrained; confidence behavior.

## Risk Notes

- This is a deterministic V1 baseline, not a claim that V1 should pass every V2 scenario.
- The report captures title ordering, signal families, expected concepts, expected penalties, and confidence expectations before V2 scorer semantics change.
- Known misses are useful because they define what V2 should improve without tuning against hidden behavior.
- Live TMDb latency and phone-sized dogfood remain later acceptance gates.
