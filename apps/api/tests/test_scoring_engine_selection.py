import unittest

from movie_night_mediator.domain.models import (
    Candidate,
    AudienceMode,
    HouseholdDefaults,
    MediaType,
    PersonCandidateConstraint,
    ProfileTasteEvidence,
    ScoringRequest,
    ScoringSessionReaction,
    SessionContext,
    SessionMode,
    TonightIntentContract,
    TonightIntentSignal,
    UserProfile,
)
from movie_night_mediator.scoring import (
    HeuristicScorer,
    ScoringEngineId,
    V2ContractScorer,
    build_recommendation_scorer,
)


class ScoringEngineSelectionTest(unittest.TestCase):
    def test_v2_contract_is_default(self) -> None:
        scorer = build_recommendation_scorer()

        self.assertIsInstance(scorer, V2ContractScorer)

    def test_v1_heuristic_can_be_selected_for_rollback(self) -> None:
        scorer = build_recommendation_scorer(ScoringEngineId.V1_HEURISTIC)

        self.assertIsInstance(scorer, HeuristicScorer)

    def test_v2_contract_uses_profile_concepts_by_default(self) -> None:
        request = ScoringRequest(
            session=SessionContext(session_id="v2-contract-test"),
            household_defaults=HouseholdDefaults(),
            users=(
                UserProfile(
                    user_id="solo",
                    role="solo",
                    display_label="Solo",
                    taste_profile_evidence=(
                        ProfileTasteEvidence(
                            source="taste_lab",
                            source_movie_id="fixture:first-contact-favorite",
                            title="First Contact Favorite",
                            preference_value=1.0,
                        ),
                    ),
                ),
            ),
            candidates=(
                Candidate(
                    source_movie_id="fixture:generic",
                    title="Generic Pick",
                    media_type=MediaType.MOVIE,
                    providers=("Prime Video",),
                ),
                Candidate(
                    source_movie_id="fixture:deep-space",
                    title="Deep Space",
                    media_type=MediaType.MOVIE,
                    overview="A cerebral first contact story.",
                    providers=("Prime Video",),
                    enrichment_feature_scores={"first-contact": 0.94},
                ),
            ),
        )

        v1 = build_recommendation_scorer(ScoringEngineId.V1_HEURISTIC).score(request)
        v2 = build_recommendation_scorer().score(request)

        self.assertEqual(
            [candidate.title for candidate in v1.ranked_candidates],
            ["Generic Pick", "Deep Space"],
        )
        self.assertEqual(
            [candidate.title for candidate in v2.ranked_candidates],
            ["Deep Space", "Generic Pick"],
        )
        self.assertEqual(v1.scorer_version, "v1_heuristic")
        self.assertEqual(v2.scorer_version, "v2_contract")
        self.assertIsNotNone(v2.confidence_score)
        self.assertIn(v2.confidence_label, {"low", "medium", "high"})
        self.assertIn(
            "profile_concept:likes:first-contact",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )
        self.assertEqual(v2.partial_support_notes, ())

    def test_unknown_engine_falls_back_to_v1(self) -> None:
        scorer = build_recommendation_scorer("unknown")

        self.assertIsInstance(scorer, HeuristicScorer)

    def test_v2_contract_uses_structured_nudge_signals_and_partial_notes(self) -> None:
        request = ScoringRequest(
            session=SessionContext(
                session_id="v2-nudge-contract",
                person_constraints=(
                    PersonCandidateConstraint(
                        raw_name="Josh Brolin",
                        normalized_name="josh brolin",
                    ),
                ),
                tonight_intents=(
                    TonightIntentContract(
                        raw_text="cozy but not bleak with Josh Brolin",
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
                        unsupported_notes=("water motif is not scored yet",),
                        person_names=("Josh Brolin",),
                        confidence="high",
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
                            source_movie_id="fixture:first-contact",
                            title="First Contact Favorite",
                            preference_value=1.0,
                        ),
                    ),
                ),
            ),
            candidates=(
                Candidate(
                    source_movie_id="fixture:bleak",
                    title="Bleak Pick",
                    media_type=MediaType.MOVIE,
                    overview="A bleak drama.",
                    providers=("Prime Video",),
                ),
                Candidate(
                    source_movie_id="fixture:cozy",
                    title="Cozy Pick",
                    media_type=MediaType.MOVIE,
                    overview="A cozy mystery.",
                    providers=("Prime Video",),
                    matched_person_names=("Josh Brolin",),
                ),
            ),
        )

        v1 = build_recommendation_scorer(ScoringEngineId.V1_HEURISTIC).score(request)
        v2 = build_recommendation_scorer(ScoringEngineId.V2_CONTRACT).score(request)

        self.assertEqual(
            [candidate.title for candidate in v1.ranked_candidates],
            ["Bleak Pick", "Cozy Pick"],
        )
        self.assertEqual(
            [candidate.title for candidate in v2.ranked_candidates],
            ["Cozy Pick", "Bleak Pick"],
        )
        self.assertIn(
            "nudge_signal:include:cozy",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )
        self.assertIn(
            "nudge_person:Josh Brolin",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )
        bleak = next(
            candidate
            for candidate in v2.ranked_candidates
            if candidate.title == "Bleak Pick"
        )
        self.assertIn("nudge_signal:avoid:bleak", bleak.dominant_penalties)
        self.assertEqual(
            v2.partial_support_notes,
            ("water motif is not scored yet",),
        )

    def test_v2_negative_nudge_penalizes_family_animation_without_banning_light_picks(
        self,
    ) -> None:
        request = ScoringRequest(
            session=SessionContext(
                session_id="v2-negative-nudge-contract",
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
                        confidence="high",
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
                            source_movie_id="fixture:first-contact",
                            title="First Contact Favorite",
                            preference_value=1.0,
                        ),
                    ),
                ),
            ),
            candidates=(
                Candidate(
                    source_movie_id="fixture:animated",
                    title="Animated Family Pick",
                    media_type=MediaType.MOVIE,
                    genres=("Animation", "Family"),
                    overview="A colorful cartoonish adventure for kids.",
                    providers=("Prime Video",),
                ),
                Candidate(
                    source_movie_id="fixture:light",
                    title="Light Comedy Pick",
                    media_type=MediaType.MOVIE,
                    genres=("Comedy",),
                    overview="A witty light comedy.",
                    providers=("Prime Video",),
                ),
            ),
        )

        v2 = build_recommendation_scorer(ScoringEngineId.V2_CONTRACT).score(request)

        self.assertEqual(
            [candidate.title for candidate in v2.ranked_candidates],
            ["Light Comedy Pick", "Animated Family Pick"],
        )
        animated = v2.ranked_candidates[1]
        self.assertTrue(animated.hard_filter_pass)
        self.assertIn("nudge_signal:avoid:family", animated.dominant_penalties)
        self.assertIn("nudge_signal:avoid:animation", animated.dominant_penalties)
        self.assertEqual(v2.partial_support_notes, ())

    def test_v2_reports_negative_nudge_when_metadata_cannot_verify_it(self) -> None:
        request = ScoringRequest(
            session=SessionContext(
                session_id="v2-unverified-negative-nudge",
                tonight_intents=(
                    TonightIntentContract(
                        raw_text="nothing saccharine",
                        signals=(
                            TonightIntentSignal(
                                concept="saccharine",
                                polarity="negative",
                                intensity=1.0,
                                confidence="high",
                            ),
                        ),
                        confidence="high",
                    ),
                ),
            ),
            household_defaults=HouseholdDefaults(),
            users=(
                UserProfile(
                    user_id="solo",
                    role="solo",
                    display_label="Solo",
                ),
            ),
            candidates=(
                Candidate(
                    source_movie_id="fixture:mystery",
                    title="Mystery Pick",
                    media_type=MediaType.MOVIE,
                    genres=("Mystery",),
                    overview="A witty whodunit.",
                    providers=("Prime Video",),
                ),
            ),
        )

        v2 = build_recommendation_scorer(ScoringEngineId.V2_CONTRACT).score(request)

        self.assertEqual(
            v2.partial_support_notes,
            (
                "Could not verify avoided signal against shortlist metadata: saccharine.",
            ),
        )

    def test_v2_solo_fit_uses_richer_metadata_families(self) -> None:
        request = ScoringRequest(
            session=SessionContext(
                session_id="v2-solo-metadata-fit",
                audience_mode=AudienceMode.SOLO,
            ),
            household_defaults=HouseholdDefaults(),
            users=(
                UserProfile(
                    user_id="solo",
                    role="solo",
                    display_label="Solo",
                ),
            ),
            candidates=(
                Candidate(
                    source_movie_id="fixture:sparse",
                    title="Sparse Pick",
                    media_type=MediaType.MOVIE,
                    providers=("Prime Video",),
                ),
                Candidate(
                    source_movie_id="fixture:rich",
                    title="Rich Metadata Pick",
                    media_type=MediaType.MOVIE,
                    runtime_min=92,
                    genres=("Mystery",),
                    overview="A witty whodunit with a cozy ensemble.",
                    top_cast=("Ana de Armas",),
                    providers=("Prime Video",),
                    original_language="en",
                    spoken_languages=("en",),
                    enrichment_status="enriched",
                    enrichment_provider="local-fixture",
                    enrichment_feature_scores={
                        "whodunit": 0.95,
                        "witty": 0.9,
                    },
                ),
            ),
        )

        v1 = build_recommendation_scorer(ScoringEngineId.V1_HEURISTIC).score(request)
        v2 = build_recommendation_scorer(ScoringEngineId.V2_CONTRACT).score(request)

        self.assertEqual(
            [candidate.title for candidate in v1.ranked_candidates],
            ["Sparse Pick", "Rich Metadata Pick"],
        )
        self.assertEqual(
            [candidate.title for candidate in v2.ranked_candidates],
            ["Rich Metadata Pick", "Sparse Pick"],
        )
        self.assertIn(
            "metadata:feature_tags",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )
        self.assertIn(
            "metadata:overview_themes",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )
        self.assertIn(
            "metadata:runtime",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )
        self.assertIn(
            "metadata:language",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )

    def test_v2_sparse_candidate_remains_rankable_with_fallback_evidence(self) -> None:
        request = ScoringRequest(
            session=SessionContext(
                session_id="v2-sparse-metadata-fallback",
                audience_mode=AudienceMode.SOLO,
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
                            source_movie_id="fixture:first-contact",
                            title="First Contact Favorite",
                            preference_value=1.0,
                        ),
                    ),
                ),
            ),
            candidates=(
                Candidate(
                    source_movie_id="fixture:sparse",
                    title="Sparse Pick",
                    media_type=MediaType.MOVIE,
                    providers=("Prime Video",),
                    enrichment_status="fallback",
                    enrichment_provider="tmdb-metadata-fallback",
                ),
            ),
        )

        v2 = build_recommendation_scorer(ScoringEngineId.V2_CONTRACT).score(request)

        self.assertEqual(len(v2.ranked_candidates), 1)
        self.assertTrue(v2.ranked_candidates[0].hard_filter_pass)
        self.assertIn(
            "metadata:fallback",
            v2.ranked_candidates[0].dominant_penalties,
        )
        self.assertEqual(v2.fallback_reason, "top_candidate_uses_metadata_fallback")
        self.assertTrue(v2.is_uncertain)
        self.assertEqual(v2.confidence_label, "low")
        self.assertEqual(
            v2.uncertainty_reason,
            "Top V2 candidate relies on sparse fallback metadata.",
        )

    def test_v2_marks_no_strong_match_without_dropping_eligible_candidates(self) -> None:
        request = ScoringRequest(
            session=SessionContext(
                session_id="v2-no-strong-match",
                audience_mode=AudienceMode.SOLO,
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
                            source_movie_id="fixture:first-contact",
                            title="First Contact Favorite",
                            preference_value=1.0,
                        ),
                    ),
                ),
            ),
            candidates=(
                Candidate(
                    source_movie_id="fixture:generic-1",
                    title="Generic Pick One",
                    media_type=MediaType.MOVIE,
                    providers=("Prime Video",),
                    enrichment_status="enriched",
                    enrichment_provider="local-fixture",
                ),
                Candidate(
                    source_movie_id="fixture:generic-2",
                    title="Generic Pick Two",
                    media_type=MediaType.MOVIE,
                    providers=("Prime Video",),
                    enrichment_status="enriched",
                    enrichment_provider="local-fixture",
                ),
            ),
        )

        v2 = build_recommendation_scorer(ScoringEngineId.V2_CONTRACT).score(request)

        self.assertEqual(len(v2.ranked_candidates), 2)
        self.assertTrue(v2.is_uncertain)
        self.assertEqual(v2.confidence_label, "low")
        self.assertEqual(
            v2.uncertainty_reason,
            "No strong V2 match stood out from the eligible shortlist.",
        )
        self.assertIn("Broaden", v2.recommended_follow_up or "")

    def test_v2_recent_post_watch_memory_outweighs_old_weak_session_reaction(
        self,
    ) -> None:
        request = ScoringRequest(
            session=SessionContext(session_id="v2-memory-source-weighting"),
            household_defaults=HouseholdDefaults(),
            users=(
                UserProfile(
                    user_id="solo",
                    role="solo",
                    display_label="Solo",
                    taste_profile_evidence=(
                        ProfileTasteEvidence(
                            source="taste_lab",
                            source_movie_id="fixture:old-witty",
                            title="Old Witty Favorite",
                            preference_value=0.35,
                            rated_at="2025-01-01T12:00:00Z",
                        ),
                        ProfileTasteEvidence(
                            source="memory:post_watch_feedback",
                            source_movie_id="fixture:first-contact",
                            title="First Contact Favorite",
                            preference_value=1.0,
                            rated_at="2026-07-07T12:00:00Z",
                        ),
                    ),
                ),
            ),
            candidates=(
                Candidate(
                    source_movie_id="fixture:witty",
                    title="Witty Pick",
                    media_type=MediaType.MOVIE,
                    overview="A witty comedy.",
                    providers=("Prime Video",),
                ),
                Candidate(
                    source_movie_id="fixture:first-contact",
                    title="First Contact Pick",
                    media_type=MediaType.MOVIE,
                    overview="A cerebral first contact story.",
                    providers=("Prime Video",),
                ),
            ),
            session_reactions=(
                ScoringSessionReaction(
                    source_movie_id="fixture:witty",
                    reaction_label="interested",
                    title="Witty Pick",
                ),
            ),
        )

        v2 = build_recommendation_scorer(ScoringEngineId.V2_CONTRACT).score(request)

        self.assertEqual(
            [candidate.title for candidate in v2.ranked_candidates],
            ["First Contact Pick", "Witty Pick"],
        )
        self.assertIn(
            "memory_source:post_watch_feedback:first-contact",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )
        witty = next(
            candidate
            for candidate in v2.ranked_candidates
            if candidate.title == "Witty Pick"
        )
        self.assertIn(
            "memory_source:session_reaction",
            witty.dominant_positive_evidence,
        )

    def test_v2_repeated_concept_memory_outweighs_isolated_signal(self) -> None:
        request = ScoringRequest(
            session=SessionContext(session_id="v2-repeated-memory"),
            household_defaults=HouseholdDefaults(),
            users=(
                UserProfile(
                    user_id="solo",
                    role="solo",
                    display_label="Solo",
                    taste_profile_evidence=(
                        ProfileTasteEvidence(
                            source="taste_lab",
                            source_movie_id="fixture:first-contact-1",
                            title="First Contact Favorite",
                            preference_value=1.0,
                            rated_at="2026-07-01T12:00:00Z",
                        ),
                        ProfileTasteEvidence(
                            source="memory:app_memory",
                            source_movie_id="fixture:first-contact-2",
                            title="Cerebral First Contact Memory",
                            preference_value=1.0,
                            rated_at="2026-07-02T12:00:00Z",
                        ),
                        ProfileTasteEvidence(
                            source="taste_lab",
                            source_movie_id="fixture:witty",
                            title="Witty Favorite",
                            preference_value=1.0,
                            rated_at="2026-07-01T12:00:00Z",
                        ),
                    ),
                ),
            ),
            candidates=(
                Candidate(
                    source_movie_id="fixture:witty",
                    title="Witty Pick",
                    media_type=MediaType.MOVIE,
                    overview="A witty comedy.",
                    providers=("Prime Video",),
                ),
                Candidate(
                    source_movie_id="fixture:first-contact",
                    title="First Contact Pick",
                    media_type=MediaType.MOVIE,
                    overview="A cerebral first contact story.",
                    providers=("Prime Video",),
                ),
            ),
        )

        v2 = build_recommendation_scorer(ScoringEngineId.V2_CONTRACT).score(request)

        self.assertEqual(
            [candidate.title for candidate in v2.ranked_candidates],
            ["First Contact Pick", "Witty Pick"],
        )
        self.assertIn(
            "profile_concept:likes:first-contact",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )

    def test_v2_compromise_mode_promotes_bridge_pick_over_veto_risk(self) -> None:
        request = ScoringRequest(
            session=SessionContext(
                session_id="v2-shared-compromise",
                audience_mode=AudienceMode.SHARED,
                session_mode=SessionMode.COMPROMISE,
            ),
            household_defaults=HouseholdDefaults(),
            users=(
                UserProfile(
                    user_id="user-a",
                    role="husband",
                    display_label="Husband",
                    taste_profile_evidence=(
                        ProfileTasteEvidence(
                            source="taste_lab",
                            source_movie_id="fixture:action-1",
                            title="Action Favorite 1",
                            genres=("Action",),
                            preference_value=1.0,
                        ),
                        ProfileTasteEvidence(
                            source="taste_lab",
                            source_movie_id="fixture:action-2",
                            title="Action Favorite 2",
                            genres=("Action",),
                            preference_value=1.0,
                        ),
                    ),
                ),
                UserProfile(
                    user_id="user-b",
                    role="wife",
                    display_label="Wife",
                    taste_profile_evidence=(
                        ProfileTasteEvidence(
                            source="taste_lab",
                            source_movie_id="fixture:action-no-1",
                            title="Action No 1",
                            genres=("Action",),
                            preference_value=-1.0,
                        ),
                        ProfileTasteEvidence(
                            source="taste_lab",
                            source_movie_id="fixture:action-no-2",
                            title="Action No 2",
                            genres=("Action",),
                            preference_value=-1.0,
                        ),
                        ProfileTasteEvidence(
                            source="taste_lab",
                            source_movie_id="fixture:mystery",
                            title="Mystery Favorite",
                            genres=("Mystery",),
                            preference_value=1.0,
                        ),
                    ),
                ),
            ),
            candidates=(
                Candidate(
                    source_movie_id="fixture:one-sided",
                    title="One Sided Action",
                    media_type=MediaType.MOVIE,
                    genres=("Action",),
                    providers=("Prime Video",),
                ),
                Candidate(
                    source_movie_id="fixture:bridge",
                    title="Bridge Mystery",
                    media_type=MediaType.MOVIE,
                    genres=("Mystery",),
                    overview="A witty whodunit with a little high-energy momentum.",
                    providers=("Prime Video",),
                ),
            ),
        )

        v2 = build_recommendation_scorer(ScoringEngineId.V2_CONTRACT).score(request)

        self.assertEqual(
            [candidate.title for candidate in v2.ranked_candidates],
            ["Bridge Mystery", "One Sided Action"],
        )
        self.assertIn(
            "shared:overlap_strength",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )
        self.assertIn(
            "shared:bridge_value",
            v2.ranked_candidates[0].dominant_positive_evidence,
        )
        one_sided = v2.ranked_candidates[1]
        self.assertIn("shared:veto_risk", one_sided.dominant_penalties)
        self.assertIn("shared:one_sided_fit", one_sided.dominant_penalties)

    def test_v2_first_viewer_modes_still_favor_selected_viewer_with_risk_evidence(
        self,
    ) -> None:
        base_users = (
            UserProfile(
                user_id="user-a",
                role="husband",
                display_label="Husband",
                taste_profile_evidence=(
                    ProfileTasteEvidence(
                        source="taste_lab",
                        source_movie_id="fixture:action",
                        title="Action Favorite",
                        genres=("Action",),
                        preference_value=1.0,
                    ),
                ),
            ),
            UserProfile(
                user_id="user-b",
                role="wife",
                display_label="Wife",
                taste_profile_evidence=(
                    ProfileTasteEvidence(
                        source="taste_lab",
                        source_movie_id="fixture:romance",
                        title="Romance Favorite",
                        genres=("Romance",),
                        preference_value=1.0,
                    ),
                    ProfileTasteEvidence(
                        source="taste_lab",
                        source_movie_id="fixture:action-no",
                        title="Action No",
                        genres=("Action",),
                        preference_value=-1.0,
                    ),
                ),
            ),
        )
        candidates = (
            Candidate(
                source_movie_id="fixture:action",
                title="Action Pick",
                media_type=MediaType.MOVIE,
                genres=("Action",),
                providers=("Prime Video",),
            ),
            Candidate(
                source_movie_id="fixture:romance",
                title="Romance Pick",
                media_type=MediaType.MOVIE,
                genres=("Romance",),
                providers=("Prime Video",),
            ),
        )

        husband_first = build_recommendation_scorer(ScoringEngineId.V2_CONTRACT).score(
            ScoringRequest(
                session=SessionContext(
                    session_id="v2-husband-first",
                    audience_mode=AudienceMode.SHARED,
                    session_mode=SessionMode.HUSBAND_FIRST,
                ),
                household_defaults=HouseholdDefaults(),
                users=base_users,
                candidates=candidates,
            )
        )
        wife_first = build_recommendation_scorer(ScoringEngineId.V2_CONTRACT).score(
            ScoringRequest(
                session=SessionContext(
                    session_id="v2-wife-first",
                    audience_mode=AudienceMode.SHARED,
                    session_mode=SessionMode.WIFE_FIRST,
                ),
                household_defaults=HouseholdDefaults(),
                users=base_users,
                candidates=candidates,
            )
        )

        self.assertEqual(husband_first.ranked_candidates[0].title, "Action Pick")
        self.assertIn(
            "shared:husband_first_win",
            husband_first.ranked_candidates[0].dominant_positive_evidence,
        )
        self.assertIn(
            "shared:second_viewer_weak_fit",
            husband_first.ranked_candidates[0].dominant_penalties,
        )
        self.assertEqual(wife_first.ranked_candidates[0].title, "Romance Pick")
        self.assertIn(
            "shared:wife_first_win",
            wife_first.ranked_candidates[0].dominant_positive_evidence,
        )


if __name__ == "__main__":
    unittest.main()
