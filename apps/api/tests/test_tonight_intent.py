from __future__ import annotations

import unittest

from movie_night_mediator.app.tonight_intent import (
    DeterministicTonightIntentProvider,
    TonightIntentInterpreter,
)
from movie_night_mediator.mvp_plus_2 import (
    IntentInterpretation,
    IntentInterpretationStatus,
)
from movie_night_mediator.mvp_plus_3 import (
    DirectedNudge,
    DirectedNudgeStatus,
    PersonCandidateIntent,
)


class FakeLiveIntentProvider:
    def interpret(self, text: str) -> IntentInterpretation:
        return IntentInterpretation(
            raw_text=text,
            status=IntentInterpretationStatus.CONFIRMATION_REQUIRED,
            confirmation_text="Got it: using the live-shaped provider.",
            filters={"genres": ["Comedy"]},
            soft_signals=("live-shaped",),
            confidence="high",
        )


class FakeLiveDirectedNudgeProvider(FakeLiveIntentProvider):
    def interpret_directed_nudge(self, text: str) -> DirectedNudge:
        return DirectedNudge(
            raw_text=text,
            status=DirectedNudgeStatus.CONFIRMATION_REQUIRED,
            user_facing_summary="Got it: keeping the live-shaped nudge active.",
            filters={"genres": ["Thriller"]},
            soft_signals=("live-directed",),
            confidence="high",
        )


class TonightIntentInterpreterTest(unittest.TestCase):
    def test_maps_90s_request_to_structured_filters(self) -> None:
        interpretation = DeterministicTonightIntentProvider().interpret(
            "something silly from the 90s"
        )

        self.assertEqual(
            interpretation.status,
            IntentInterpretationStatus.CONFIRMATION_REQUIRED,
        )
        self.assertEqual(interpretation.filters["release_year_min"], 1990)
        self.assertEqual(interpretation.filters["release_year_max"], 1999)
        self.assertEqual(interpretation.filters["genres"], ["Comedy"])
        self.assertIn("1990-1999", interpretation.confirmation_text or "")

    def test_maps_person_request_and_seen_constraint(self) -> None:
        interpretation = DeterministicTonightIntentProvider().interpret(
            "a Mel Gibson movie I haven't seen"
        )

        self.assertEqual(interpretation.filters["people"], ["Mel Gibson"])
        self.assertTrue(interpretation.filters["exclude_watched"])
        self.assertIn("Mel Gibson", interpretation.confirmation_text or "")

    def test_maps_franchise_request_to_constraint(self) -> None:
        interpretation = DeterministicTonightIntentProvider().interpret(
            "maybe Star Wars but new to us"
        )

        self.assertEqual(interpretation.filters["franchise"], "Star Wars")
        self.assertTrue(interpretation.filters["exclude_watched"])

    def test_ambiguous_emotional_request_asks_one_clarification(self) -> None:
        interpretation = DeterministicTonightIntentProvider().interpret(
            "ugh I feel sad today"
        )

        self.assertEqual(
            interpretation.status,
            IntentInterpretationStatus.CLARIFICATION_REQUIRED,
        )
        self.assertIsNone(interpretation.confirmation_text)
        self.assertIn("comforting", interpretation.clarification_question or "")
        self.assertIn("matches the mood", interpretation.clarification_question or "")

    def test_interpreter_can_delegate_to_live_shaped_provider(self) -> None:
        interpretation = TonightIntentInterpreter(
            live_provider=FakeLiveIntentProvider()
        ).interpret("make us laugh")

        self.assertEqual(interpretation.filters, {"genres": ["Comedy"]})
        self.assertEqual(interpretation.soft_signals, ("live-shaped",))

    def test_interpreter_does_not_return_rankings(self) -> None:
        interpretation = DeterministicTonightIntentProvider().interpret(
            "something funny from the 90s"
        )

        forbidden_filter_keys = {
            "ranking",
            "rankings",
            "ranked_source_movie_ids",
            "rankedSourceMovieIds",
            "source_movie_ids",
            "sourceMovieIds",
        }
        self.assertTrue(forbidden_filter_keys.isdisjoint(interpretation.filters))

    def test_directed_nudge_maps_scary_but_not_bleak(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "scary but not bleak"
        )

        self.assertEqual(nudge.status, DirectedNudgeStatus.CONFIRMATION_REQUIRED)
        self.assertEqual(nudge.filters["genres"], ["Horror"])
        self.assertIn("horror", nudge.soft_signals)
        self.assertIn("bleak", nudge.excluded_signals)
        self.assertNotIn("bleak", nudge.soft_signals)
        self.assertIn("not bleak", nudge.user_facing_summary or "")

    def test_directed_nudge_maps_sad_but_beautiful_without_clarifying(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "sad but beautiful"
        )

        self.assertEqual(nudge.status, DirectedNudgeStatus.CONFIRMATION_REQUIRED)
        self.assertIn("sad", nudge.soft_signals)
        self.assertIn("beautiful", nudge.soft_signals)
        self.assertIsNone(nudge.clarification_question)

    def test_directed_nudge_maps_90s_thriller(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "90s thriller"
        )

        self.assertEqual(nudge.filters["release_year_min"], 1990)
        self.assertEqual(nudge.filters["release_year_max"], 1999)
        self.assertEqual(nudge.filters["genres"], ["Thriller"])
        self.assertIn("thriller", nudge.soft_signals)

    def test_directed_nudge_maps_subtitle_exclusion(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "nothing with subtitles tonight"
        )

        self.assertTrue(nudge.filters["exclude_subtitled"])
        self.assertIn("subtitles", nudge.excluded_signals)
        self.assertIn("tonight", nudge.soft_signals)
        self.assertIn("without subtitles", nudge.user_facing_summary or "")

    def test_directed_nudge_maps_person_intent_for_candidate_generation(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "Jack Nicholson in it"
        )

        self.assertEqual(
            nudge.person_intents,
            (
                PersonCandidateIntent(
                    raw_name="Jack Nicholson",
                    normalized_name="jack nicholson",
                ),
            ),
        )
        self.assertEqual(nudge.filters["people"], ["Jack Nicholson"])
        self.assertTrue(nudge.has_person_intent)

    def test_directed_nudge_asks_clarification_for_ambiguous_emotion(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge("sad")

        self.assertEqual(nudge.status, DirectedNudgeStatus.CLARIFICATION_REQUIRED)
        self.assertIsNone(nudge.user_facing_summary)
        self.assertIn("comforting", nudge.clarification_question or "")
        self.assertIn("matches the mood", nudge.clarification_question or "")

    def test_directed_nudge_live_provider_still_returns_structured_context(self) -> None:
        nudge = TonightIntentInterpreter(
            live_provider=FakeLiveDirectedNudgeProvider()
        ).interpret_directed_nudge("90s thriller")

        self.assertEqual(nudge.filters, {"genres": ["Thriller"]})
        self.assertEqual(nudge.soft_signals, ("live-directed",))
        self.assertFalse(
            {
                "ranking",
                "rankings",
                "ranked_source_movie_ids",
                "rankedSourceMovieIds",
                "source_movie_ids",
                "sourceMovieIds",
            }.intersection(nudge.filters)
        )


if __name__ == "__main__":
    unittest.main()
