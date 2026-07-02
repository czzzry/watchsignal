from __future__ import annotations

import unittest

from movie_night_mediator.mvp_plus_2 import (
    CandidateEnrichment,
    CandidateEnrichmentStatus,
    EvaluationCoverage,
    IntentInterpretation,
    IntentInterpretationStatus,
    ProfileIdentity,
    ScoringEvidence,
    SessionContinuationKind,
    SessionContinuationRequest,
    SignalContribution,
    WatchlistEntry,
)


class MvpPlus2ContractsTest(unittest.TestCase):
    def test_profile_identity_requires_label_and_visual_identity(self) -> None:
        identity = ProfileIdentity(
            profile_id=" husband ",
            display_label=" Alex ",
            avatar_key="spark",
            color_key="teal",
        )

        self.assertEqual(identity.profile_id, "husband")
        self.assertEqual(identity.display_label, "Alex")
        self.assertEqual(identity.avatar_key, "spark")
        self.assertEqual(identity.color_key, "teal")

    def test_watchlist_entries_are_shared_memory_not_taste_signals(self) -> None:
        entry = WatchlistEntry(
            household_id="default-household",
            source_movie_id="tmdb:603",
            title="The Matrix",
            saved_at="2026-07-02T10:00:00Z",
            saved_by_profile_id="husband",
        )

        self.assertFalse(entry.is_taste_signal)
        self.assertEqual(entry.saved_by_profile_id, "husband")

    def test_intent_interpretation_supports_confirm_before_apply(self) -> None:
        interpretation = IntentInterpretation(
            raw_text="something silly from the 90s",
            status=IntentInterpretationStatus.CONFIRMATION_REQUIRED,
            confirmation_text="Got it: something funny and light from the 1990s.",
            filters={"year_range": (1990, 1999)},
            soft_signals=("silly", "comedy"),
            confidence="high",
        )

        self.assertEqual(interpretation.filters["year_range"], (1990, 1999))
        self.assertEqual(interpretation.soft_signals, ("silly", "comedy"))

    def test_ambiguous_emotional_intent_requires_clarification(self) -> None:
        interpretation = IntentInterpretation(
            raw_text="ugh, I feel sad today",
            status=IntentInterpretationStatus.CLARIFICATION_REQUIRED,
            clarification_question=(
                "Do you want something that matches the mood or something comforting?"
            ),
            soft_signals=("sad",),
        )

        self.assertIn("matches the mood", interpretation.clarification_question or "")

    def test_rejects_mixed_confirmation_and_clarification_intent(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot include a clarification"):
            IntentInterpretation(
                raw_text="sad",
                status=IntentInterpretationStatus.CONFIRMATION_REQUIRED,
                confirmation_text="Got it.",
                clarification_question="Cheer up or match the mood?",
            )

    def test_session_continuation_distinguishes_show_more_and_steer_next(self) -> None:
        show_more = SessionContinuationRequest(
            session_id="session-1",
            kind=SessionContinuationKind.SHOW_MORE,
            already_shown_source_movie_ids=("tmdb:1", "tmdb:2"),
            active_intent_ids=("intent-1",),
        )
        steer_next = SessionContinuationRequest(
            session_id="session-1",
            kind=SessionContinuationKind.STEER_NEXT,
            already_shown_source_movie_ids=("tmdb:1", "tmdb:2"),
            active_intent_ids=("intent-1",),
            steer_text="actually something set in New York",
        )

        self.assertIsNone(show_more.steer_text)
        self.assertEqual(steer_next.steer_text, "actually something set in New York")

    def test_show_more_rejects_steer_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "Show-more"):
            SessionContinuationRequest(
                session_id="session-1",
                kind=SessionContinuationKind.SHOW_MORE,
                already_shown_source_movie_ids=("tmdb:1",),
                steer_text="set in fall",
            )

    def test_candidate_enrichment_allows_rich_and_fallback_candidates(self) -> None:
        enriched = CandidateEnrichment(
            source_movie_id="tmdb:603",
            status=CandidateEnrichmentStatus.ENRICHED,
            provider="movielens_tag_genome",
            matched_source_movie_id="movielens:2571",
            feature_scores={"mind-bending": 0.91, "stylized": 0.63},
        )
        fallback = CandidateEnrichment(
            source_movie_id="tmdb:999",
            status=CandidateEnrichmentStatus.FALLBACK,
            provider="tmdb",
        )

        self.assertTrue(enriched.is_enriched)
        self.assertFalse(fallback.is_enriched)

    def test_scoring_evidence_names_signal_families(self) -> None:
        evidence = ScoringEvidence(
            source_movie_id="tmdb:603",
            enrichment_status=CandidateEnrichmentStatus.ENRICHED,
            contributions=(
                SignalContribution("genre", "Sci-Fi", 0.2),
                SignalContribution("title_similarity", "Arrival", 0.4),
                SignalContribution("feature_tag", "mind-bending", 0.3),
                SignalContribution("tonight_intent", "90s", 0.1),
                SignalContribution("fallback", "tmdb-only", 0.0),
            ),
        )

        self.assertEqual(
            evidence.signal_families,
            (
                "genre",
                "title_similarity",
                "feature_tag",
                "tonight_intent",
                "fallback",
            ),
        )

    def test_evaluation_coverage_reports_enrichment_rate(self) -> None:
        coverage = EvaluationCoverage(
            scenario_name="fixture",
            candidate_count=5,
            enriched_candidate_count=3,
            fallback_candidate_count=2,
        )

        self.assertEqual(coverage.enrichment_rate, 0.6)

    def test_evaluation_coverage_rejects_mismatched_counts(self) -> None:
        with self.assertRaisesRegex(ValueError, "add up"):
            EvaluationCoverage(
                scenario_name="fixture",
                candidate_count=5,
                enriched_candidate_count=4,
                fallback_candidate_count=2,
            )


if __name__ == "__main__":
    unittest.main()
