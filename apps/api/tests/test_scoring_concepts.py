import unittest

from movie_night_mediator.domain.models import (
    Candidate,
    HouseholdDefaults,
    MediaType,
    OnboardingSeed,
    ProfileTasteEvidence,
    ScoringRequest,
    SessionContext,
    TonightIntentContract,
    TonightIntentSignal,
    UserProfile,
)
from movie_night_mediator.scoring import (
    ScoringConceptRegistry,
    ScoringEngineId,
    build_recommendation_scorer,
)


class ScoringConceptRegistryTest(unittest.TestCase):
    def test_maps_metadata_to_stable_concept_labels(self) -> None:
        candidate = Candidate(
            source_movie_id="fixture:arrival",
            title="Arrival",
            media_type=MediaType.MOVIE,
            genres=("Sci-Fi", "Drama"),
            overview="A cerebral first contact story.",
            providers=("Prime Video",),
            enrichment_feature_scores={"first-contact": 0.94, "slow-burn": 0.5},
        )

        evidence = ScoringConceptRegistry().concepts_for_candidate(candidate)
        concepts = {item.concept for item in evidence}

        self.assertIn("cerebral", concepts)
        self.assertIn("first-contact", concepts)
        self.assertIn("slow", concepts)

    def test_maps_negative_nudge_to_candidate_concept_penalty(self) -> None:
        candidate = Candidate(
            source_movie_id="fixture:animated",
            title="Animated Family Pick",
            media_type=MediaType.MOVIE,
            genres=("Animation", "Family"),
            overview="A colorful cartoonish adventure for kids.",
            providers=("Prime Video",),
        )

        evidence = ScoringConceptRegistry().concepts_for_candidate(
            candidate,
            nudge_text="no kids movies and no cartoonish stuff",
        )
        negative_concepts = {
            item.concept for item in evidence if item.polarity == "negative"
        }

        self.assertIn("family", negative_concepts)
        self.assertIn("animation", negative_concepts)

    def test_maps_structured_nudge_signals_to_candidate_concepts(self) -> None:
        candidate = Candidate(
            source_movie_id="fixture:cozy",
            title="Cozy Mystery",
            media_type=MediaType.MOVIE,
            overview="A cozy whodunit.",
            providers=("Prime Video",),
        )

        evidence = ScoringConceptRegistry().concepts_for_candidate(
            candidate,
            tonight_intents=(
                TonightIntentContract(
                    raw_text="cozy but not bleak",
                    signals=(
                        TonightIntentSignal(
                            concept="cozy",
                            polarity="positive",
                            intensity=1.0,
                            confidence="high",
                        ),
                        TonightIntentSignal(
                            concept="bleak",
                            polarity="negative",
                            intensity=1.0,
                            confidence="high",
                        ),
                    ),
                ),
            ),
        )

        self.assertIn(
            ("cozy", "positive", "nudge_positive"),
            {(item.concept, item.polarity, item.source) for item in evidence},
        )
        self.assertNotIn(
            ("bleak", "negative", "nudge_negative"),
            {(item.concept, item.polarity, item.source) for item in evidence},
        )

    def test_compiles_profile_evidence_into_concept_affinities(self) -> None:
        user = UserProfile(
            user_id="solo",
            role="solo",
            display_label="Solo",
            onboarding_seeds=(
                OnboardingSeed(
                    title="No Cartoon",
                    label="no",
                    genres=("Animation",),
                    notes="cartoonish kids adventure",
                ),
            ),
            taste_profile_evidence=(
                ProfileTasteEvidence(
                    source="memory:post_watch_feedback",
                    source_movie_id="fixture:first-contact",
                    title="First Contact Favorite",
                    preference_value=1.0,
                ),
            ),
        )

        affinities = ScoringConceptRegistry().affinities_for_user(user)
        values_by_concept = {item.concept: item.value for item in affinities}

        self.assertGreater(values_by_concept["first-contact"], 0)
        self.assertLess(values_by_concept["animation"], 0)

    def test_v2_contract_exposes_profile_fit_and_nudge_penalties(self) -> None:
        request = ScoringRequest(
            session=SessionContext(
                session_id="concept-v2-contract",
                mood_text="no kids movies and no cartoonish stuff",
                tonight_intents=(
                    TonightIntentContract(
                        raw_text="no kids movies and no cartoonish stuff",
                        signals=(
                            TonightIntentSignal(
                                concept="family",
                                polarity="negative",
                                intensity=1.0,
                                confidence="high",
                            ),
                            TonightIntentSignal(
                                concept="animation",
                                polarity="negative",
                                intensity=1.0,
                                confidence="high",
                            ),
                        ),
                    ),
                ),
            ),
            household_defaults=HouseholdDefaults(),
            users=(
                UserProfile(
                    user_id="solo",
                    role="solo",
                    display_label="Solo",
                    taste_profile_evidence=(
                        ProfileTasteEvidence(
                            source="taste_lab",
                            source_movie_id="fixture:whodunit-favorite",
                            title="Witty Whodunit Favorite",
                            preference_value=1.0,
                        ),
                    ),
                ),
            ),
            candidates=(
                Candidate(
                    source_movie_id="fixture:knives-out",
                    title="Knives Out",
                    media_type=MediaType.MOVIE,
                    genres=("Mystery", "Comedy"),
                    overview="A witty whodunit.",
                    providers=("Prime Video",),
                    enrichment_feature_scores={"whodunit": 0.96, "witty": 0.88},
                ),
                Candidate(
                    source_movie_id="fixture:animated",
                    title="Animated Family Pick",
                    media_type=MediaType.MOVIE,
                    genres=("Animation", "Family"),
                    overview="A colorful cartoonish adventure for kids.",
                    providers=("Prime Video",),
                ),
            ),
        )

        v1 = build_recommendation_scorer(ScoringEngineId.V1_HEURISTIC).score(request)
        v2 = build_recommendation_scorer(ScoringEngineId.V2_CONTRACT).score(request)

        self.assertEqual(
            [candidate.title for candidate in v2.ranked_candidates],
            [candidate.title for candidate in v1.ranked_candidates],
        )
        self.assertIn(
            "concept:mystery",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )
        self.assertIn(
            "profile_concept:likes:mystery",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )
        animated = next(
            candidate
            for candidate in v2.ranked_candidates
            if candidate.title == "Animated Family Pick"
        )
        self.assertIn("concept:family", animated.dominant_penalties)
        self.assertIn("concept:animation", animated.dominant_penalties)
        self.assertIn("nudge_signal:avoid:family", animated.dominant_penalties)
        self.assertIn("nudge_signal:avoid:animation", animated.dominant_penalties)


if __name__ == "__main__":
    unittest.main()
