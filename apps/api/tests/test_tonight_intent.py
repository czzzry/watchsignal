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


if __name__ == "__main__":
    unittest.main()
