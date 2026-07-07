from __future__ import annotations

import unittest

from movie_night_mediator.mvp_plus_3 import (
    AcceptanceGateContract,
    AcceptanceProofRequirement,
    BookmarkContract,
    DirectedNudge,
    DirectedNudgeStatus,
    EvidenceFamily,
    FiveMoreAction,
    FiveMoreRequest,
    MvpPlus3PhaseContract,
    PersonCandidateIntent,
    ProfileIdentity,
    RecommendationEvidenceContract,
    SelectedRecommendationProfiles,
    TasteLabRatingOwnership,
)


class MvpPlus3ContractsTest(unittest.TestCase):
    def test_profile_identity_is_stable_through_rename(self) -> None:
        profile = ProfileIdentity(
            profile_id=" cezary-tester ",
            display_label="Cezary - tester",
            household_id="default-household",
        )
        renamed = profile.renamed("Cezary")

        self.assertTrue(profile.is_tester_profile)
        self.assertEqual(renamed.profile_id, "cezary-tester")
        self.assertEqual(renamed.display_label, "Cezary")

    def test_taste_lab_rating_ownership_requires_profile_identity(self) -> None:
        rating = TasteLabRatingOwnership(
            household_id="default-household",
            profile_id="cezary-tester",
            source_movie_id="tmdb:539",
            rating_label="love",
            familiarity_label="seen",
            queue_provenance="generated-seed-queue",
            rated_at="2026-07-07T08:00:00Z",
        )

        self.assertEqual(rating.profile_id, "cezary-tester")

    def test_selected_profiles_preserve_two_person_movie_night(self) -> None:
        selected = SelectedRecommendationProfiles(
            household_id="default-household",
            profile_ids=("cezary-tester", "partner"),
            active_profile_order=("partner", "cezary-tester"),
        )

        self.assertTrue(selected.supports_shared_movie_night)
        self.assertEqual(selected.active_profile_order, ("partner", "cezary-tester"))

    def test_selected_profiles_reject_order_that_does_not_match_profiles(self) -> None:
        with self.assertRaisesRegex(ValueError, "must match"):
            SelectedRecommendationProfiles(
                household_id="default-household",
                profile_ids=("cezary-tester", "partner"),
                active_profile_order=("cezary-tester", "guest"),
            )

    def test_directed_nudge_supports_person_intent_and_excluded_signals(self) -> None:
        nudge = DirectedNudge(
            raw_text="scary but not bleak, with Jack Nicholson in it",
            status=DirectedNudgeStatus.CONFIRMATION_REQUIRED,
            user_facing_summary="Scary, not bleak, and starring Jack Nicholson.",
            filters={"genres": ["Horror"]},
            soft_signals=("scary",),
            excluded_signals=("bleak",),
            person_intents=(
                PersonCandidateIntent(
                    raw_name="Jack Nicholson",
                    normalized_name="jack nicholson",
                ),
            ),
            confidence="high",
        )

        self.assertTrue(nudge.has_person_intent)
        self.assertEqual(nudge.excluded_signals, ("bleak",))

    def test_directed_nudge_requires_clarification_for_ambiguous_status(self) -> None:
        with self.assertRaisesRegex(ValueError, "clarification question"):
            DirectedNudge(
                raw_text="sad",
                status=DirectedNudgeStatus.CLARIFICATION_REQUIRED,
            )

    def test_five_more_models_redo_semantics(self) -> None:
        add_nudge = FiveMoreRequest(
            session_id="session-1",
            action=FiveMoreAction.ADD_NUDGE,
            already_shown_source_movie_ids=("tmdb:1", "tmdb:2"),
            active_nudge_ids=("nudge-1",),
            add_nudge_text="more like this but shorter",
        )
        more_like_this = FiveMoreRequest(
            session_id="session-1",
            action=FiveMoreAction.MORE_LIKE_THIS,
            already_shown_source_movie_ids=("tmdb:1", "tmdb:2"),
            reference_source_movie_id="tmdb:1",
        )

        self.assertEqual(add_nudge.add_nudge_text, "more like this but shorter")
        self.assertEqual(more_like_this.reference_source_movie_id, "tmdb:1")

    def test_five_more_rejects_repeats_and_invalid_action_payloads(self) -> None:
        with self.assertRaisesRegex(ValueError, "nudge text"):
            FiveMoreRequest(
                session_id="session-1",
                action=FiveMoreAction.ADD_NUDGE,
                already_shown_source_movie_ids=("tmdb:1",),
            )

        with self.assertRaisesRegex(ValueError, "reference movie"):
            FiveMoreRequest(
                session_id="session-1",
                action=FiveMoreAction.MORE_LIKE_THIS,
                already_shown_source_movie_ids=("tmdb:1",),
            )

    def test_bookmark_is_not_taste_signal_without_explicit_seed_request(self) -> None:
        bookmark = BookmarkContract(
            household_id="default-household",
            source_movie_id="tmdb:603",
            title="The Matrix",
            saved_at="2026-07-07T08:30:00Z",
            saved_by_profile_id="cezary-tester",
        )

        self.assertFalse(bookmark.is_taste_signal)
        self.assertFalse(bookmark.can_be_recommendation_seed)

    def test_bookmark_can_be_explicit_seed_without_becoming_taste_signal(self) -> None:
        bookmark = BookmarkContract(
            household_id="default-household",
            source_movie_id="tmdb:603",
            title="The Matrix",
            saved_at="2026-07-07T08:30:00Z",
            explicit_seed_requested=True,
        )

        self.assertTrue(bookmark.can_be_recommendation_seed)
        self.assertFalse(bookmark.is_taste_signal)

    def test_recommendation_evidence_separates_durable_and_tonight_context(self) -> None:
        evidence = RecommendationEvidenceContract(
            source_movie_id="tmdb:603",
            families=(
                EvidenceFamily.TASTE_LAB,
                EvidenceFamily.ACTIVE_NUDGE,
                EvidenceFamily.PERSON_MATCH,
            ),
            user_facing_summary=(
                "Taste Lab liked cerebral sci-fi, and tonight asked for Jack Nicholson."
            ),
        )

        self.assertTrue(evidence.separates_durable_and_tonight_context)

    def test_acceptance_gate_requires_all_mvp_plus_3_proofs(self) -> None:
        gate = AcceptanceGateContract(
            phase_name="Directed Discovery And Real Tester Profile",
            issue_count=10,
            required_proofs=tuple(AcceptanceProofRequirement),
        )

        self.assertTrue(gate.is_mvp_plus_3_complete_contract)

    def test_phase_contract_is_treehouse_ready_when_core_shapes_align(self) -> None:
        profile = ProfileIdentity(
            profile_id="cezary-tester",
            display_label="Cezary - tester",
            household_id="default-household",
        )
        contract = MvpPlus3PhaseContract(
            profile=profile,
            selected_profiles=SelectedRecommendationProfiles(
                household_id="default-household",
                profile_ids=("cezary-tester", "partner"),
            ),
            taste_lab_rating=TasteLabRatingOwnership(
                household_id="default-household",
                profile_id="cezary-tester",
                source_movie_id="tmdb:539",
                rating_label="love",
                familiarity_label="seen",
                queue_provenance="generated-seed-queue",
                rated_at="2026-07-07T08:00:00Z",
            ),
            directed_nudge=DirectedNudge(
                raw_text="90s thriller with Jack Nicholson",
                status=DirectedNudgeStatus.CONFIRMATION_REQUIRED,
                user_facing_summary="1990s thriller with Jack Nicholson.",
                filters={"release_year_min": 1990, "release_year_max": 1999},
                person_intents=(
                    PersonCandidateIntent(
                        raw_name="Jack Nicholson",
                        normalized_name="jack nicholson",
                    ),
                ),
            ),
            five_more_request=FiveMoreRequest(
                session_id="session-1",
                action=FiveMoreAction.SAME_DIRECTION,
                already_shown_source_movie_ids=("tmdb:1", "tmdb:2"),
            ),
            bookmark=BookmarkContract(
                household_id="default-household",
                source_movie_id="tmdb:603",
                title="The Matrix",
                saved_at="2026-07-07T08:30:00Z",
                saved_by_profile_id="cezary-tester",
            ),
            recommendation_evidence=RecommendationEvidenceContract(
                source_movie_id="tmdb:603",
                families=(EvidenceFamily.TASTE_LAB, EvidenceFamily.ACTIVE_NUDGE),
                user_facing_summary="Taste Lab and tonight's nudge both contributed.",
            ),
            acceptance_gate=AcceptanceGateContract(
                phase_name="Directed Discovery And Real Tester Profile",
                issue_count=10,
                required_proofs=tuple(AcceptanceProofRequirement),
            ),
        )

        self.assertTrue(contract.is_treehouse_ready)


if __name__ == "__main__":
    unittest.main()
