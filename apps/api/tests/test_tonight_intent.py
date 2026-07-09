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
    DirectedNudgeResolution,
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
            resolution=DirectedNudgeResolution.EXACT,
            filters={"genres": ["Thriller"]},
            soft_signals=("live-directed",),
            confidence="high",
        )


class FailingLiveDirectedNudgeProvider(FakeLiveIntentProvider):
    def interpret_directed_nudge(self, text: str) -> DirectedNudge:
        raise ValueError("live steer unavailable")


class GenericLiveDirectedNudgeProvider(FakeLiveIntentProvider):
    def interpret_directed_nudge(self, text: str) -> DirectedNudge:
        return DirectedNudge(
            raw_text=text,
            status=DirectedNudgeStatus.CONFIRMATION_REQUIRED,
            user_facing_summary="Got it: keeping this around something action-forward.",
            resolution=DirectedNudgeResolution.GUESS,
            filters={"genres": ["Action"]},
            soft_signals=("intense",),
            confidence="medium",
        )


class ConflictingLiveDirectedNudgeProvider(FakeLiveIntentProvider):
    def interpret_directed_nudge(self, text: str) -> DirectedNudge:
        return DirectedNudge(
            raw_text=text,
            status=DirectedNudgeStatus.CONFIRMATION_REQUIRED,
            user_facing_summary="Got it: keeping this around romance-forward sci-fi.",
            resolution=DirectedNudgeResolution.GUESS,
            filters={"genres": ["Romance", "Sci-Fi", "Western"]},
            soft_signals=("romance", "sci-fi", "intense"),
            excluded_signals=(),
            confidence="medium",
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

    def test_maps_lowercase_person_request_and_seen_constraint(self) -> None:
        interpretation = DeterministicTonightIntentProvider().interpret(
            "a mel gibson movie i haven't seen"
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

    def test_interpreter_keeps_base_tonight_intent_deterministic(self) -> None:
        interpretation = TonightIntentInterpreter(
            directed_nudge_provider=FakeLiveDirectedNudgeProvider()
        ).interpret("make us laugh")

        self.assertEqual(interpretation.filters, {"genres": ["Comedy"]})
        self.assertNotIn("live-shaped", interpretation.soft_signals)

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

    def test_directed_nudge_does_not_promote_negated_genres(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "severe turn-of-the-century American drama about greed, frontier capitalism, oil money, obsession, moral rot, no whimsy, no sci-fi, no romance"
        )

        self.assertEqual(nudge.resolution, DirectedNudgeResolution.EXACT)
        self.assertIn("Western", nudge.filters["genres"])
        self.assertIn("Drama", nudge.filters["genres"])
        self.assertNotIn("Sci-Fi", nudge.filters["genres"])
        self.assertNotIn("Romance", nudge.filters["genres"])
        self.assertIn("sci-fi", nudge.excluded_signals)
        self.assertIn("romance", nudge.excluded_signals)
        self.assertNotIn("sci-fi", nudge.soft_signals)
        self.assertNotIn("romance", nudge.soft_signals)

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

    def test_directed_nudge_maps_lowercase_person_intent_for_candidate_generation(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "jack nicholson should be in it"
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
        self.assertIn("Jack Nicholson", nudge.user_facing_summary or "")
        self.assertEqual(nudge.resolution, DirectedNudgeResolution.EXACT)

    def test_directed_nudge_maps_include_person_phrase(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "include Tom Cruise"
        )

        self.assertEqual(nudge.resolution, DirectedNudgeResolution.EXACT)
        self.assertEqual(nudge.filters["people"], ["Tom Cruise"])
        self.assertIn("Tom Cruise", nudge.user_facing_summary or "")

    def test_directed_nudge_ignores_auxiliary_words_in_person_phrase(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "I want Josh Brolin to be in it. But I also want water to play a key role. Ideally the score is great."
        )

        self.assertEqual(nudge.resolution, DirectedNudgeResolution.EXACT)
        self.assertEqual(nudge.filters["people"], ["Josh Brolin"])
        self.assertEqual(
            nudge.person_intents,
            (
                PersonCandidateIntent(
                    raw_name="Josh Brolin",
                    normalized_name="josh brolin",
                ),
            ),
        )
        self.assertIn("Josh Brolin", nudge.user_facing_summary or "")
        self.assertIsNotNone(nudge.unsupported_reason)

    def test_directed_nudge_maps_cartoonish_kids_request_to_animation_exclusions(
        self,
    ) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "No cartoonish kids stuff"
        )

        self.assertEqual(nudge.resolution, DirectedNudgeResolution.EXACT)
        self.assertIn("animation", nudge.excluded_signals)
        self.assertIn("family", nudge.excluded_signals)
        self.assertIn("family", nudge.user_facing_summary or "")
        self.assertIn("animation", nudge.user_facing_summary or "")

    def test_directed_nudge_maps_pixar_like_and_kids_request_to_animation_exclusions(
        self,
    ) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "no pixar-like or kids movies in general"
        )

        self.assertEqual(nudge.resolution, DirectedNudgeResolution.EXACT)
        self.assertIn("animation", nudge.excluded_signals)
        self.assertIn("family", nudge.excluded_signals)
        self.assertIn("pixar-like", nudge.excluded_signals)

    def test_directed_nudge_marks_unsupported_aesthetic_request(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "i want a very green movie"
        )

        self.assertEqual(nudge.status, DirectedNudgeStatus.CONFIRMATION_REQUIRED)
        self.assertEqual(nudge.resolution, DirectedNudgeResolution.UNSUPPORTED)
        self.assertEqual(nudge.filters, {})
        self.assertIn("cannot filter directly", nudge.user_facing_summary or "")
        self.assertIsNotNone(nudge.unsupported_reason)

    def test_directed_nudge_asks_clarification_for_ambiguous_emotion(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge("sad")

        self.assertEqual(nudge.status, DirectedNudgeStatus.CLARIFICATION_REQUIRED)
        self.assertIsNone(nudge.user_facing_summary)
        self.assertIn("comforting", nudge.clarification_question or "")
        self.assertIn("matches the mood", nudge.clarification_question or "")

    def test_directed_nudge_live_provider_still_returns_structured_context(self) -> None:
        nudge = TonightIntentInterpreter(
            directed_nudge_provider=FakeLiveDirectedNudgeProvider()
        ).interpret_directed_nudge("90s thriller")

        self.assertEqual(nudge.filters["genres"], ["Thriller"])
        self.assertEqual(nudge.filters["release_year_min"], 1990)
        self.assertEqual(nudge.filters["release_year_max"], 1999)
        self.assertIn("live-directed", nudge.soft_signals)
        self.assertIn("1990s", nudge.soft_signals)
        self.assertIn("thriller", nudge.soft_signals)
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

    def test_directed_nudge_falls_back_to_deterministic_when_live_provider_fails(
        self,
    ) -> None:
        nudge = TonightIntentInterpreter(
            directed_nudge_provider=FailingLiveDirectedNudgeProvider()
        ).interpret_directed_nudge("include Tom Cruise")

        self.assertEqual(nudge.resolution, DirectedNudgeResolution.EXACT)
        self.assertEqual(nudge.filters["people"], ["Tom Cruise"])

    def test_directed_nudge_preserves_specific_ncfom_style_cues(self) -> None:
        nudge = DeterministicTonightIntentProvider().interpret_directed_nudge(
            "west Texas desert manhunt after a drug deal gone wrong, aging sheriff, relentless killer, spare modern western, not superhero action"
        )

        self.assertEqual(nudge.resolution, DirectedNudgeResolution.EXACT)
        self.assertIn("Western", nudge.filters["genres"])
        self.assertIn("Crime", nudge.filters["genres"])
        self.assertIn("desert", nudge.soft_signals)
        self.assertIn("manhunt", nudge.soft_signals)
        self.assertIn("lawman", nudge.soft_signals)
        self.assertIn("killer", nudge.soft_signals)
        self.assertIn("superhero", nudge.excluded_signals)

    def test_interpreter_merges_live_directed_nudge_with_deterministic_specificity(
        self,
    ) -> None:
        nudge = TonightIntentInterpreter(
            directed_nudge_provider=GenericLiveDirectedNudgeProvider()
        ).interpret_directed_nudge(
            "west Texas desert manhunt after a drug deal gone wrong, aging sheriff, relentless killer, spare modern western, not superhero action"
        )

        self.assertIn("Western", nudge.filters["genres"])
        self.assertIn("Action", nudge.filters["genres"])
        self.assertIn("desert", nudge.soft_signals)
        self.assertIn("superhero", nudge.excluded_signals)

    def test_interpreter_removes_live_genres_that_conflict_with_negated_request(
        self,
    ) -> None:
        nudge = TonightIntentInterpreter(
            directed_nudge_provider=ConflictingLiveDirectedNudgeProvider()
        ).interpret_directed_nudge(
            "severe turn-of-the-century American drama about greed, frontier capitalism, oil money, obsession, moral rot, no whimsy, no sci-fi, no romance"
        )

        self.assertEqual(nudge.resolution, DirectedNudgeResolution.EXACT)
        self.assertIn("Western", nudge.filters["genres"])
        self.assertNotIn("Sci-Fi", nudge.filters["genres"])
        self.assertNotIn("Romance", nudge.filters["genres"])
        self.assertNotIn("sci-fi", nudge.soft_signals)
        self.assertNotIn("romance", nudge.soft_signals)
        self.assertIn("sci-fi", nudge.excluded_signals)
        self.assertIn("romance", nudge.excluded_signals)


if __name__ == "__main__":
    unittest.main()
