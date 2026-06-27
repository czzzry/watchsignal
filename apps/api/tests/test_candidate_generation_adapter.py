from __future__ import annotations

import unittest

from movie_night_mediator.domain.models import ProviderAccessType
from movie_night_mediator.fixtures.candidate_adapter import (
    FixtureCandidate,
    FixtureProviderAvailability,
    fixture_candidates_to_shortlist,
)
from movie_night_mediator.fixtures.demo_couple import (
    DEMO_HOUSEHOLD_DEFAULTS,
    DEMO_HUSBAND_PROFILE,
    DEMO_SHARED_SESSION,
    DEMO_WIFE_PROFILE,
    demo_candidate_shortlist,
)


class CandidateGenerationAdapterTest(unittest.TestCase):
    def test_demo_shortlist_has_stable_five_title_shape(self) -> None:
        shortlist = demo_candidate_shortlist()

        self.assertEqual(
            tuple(candidate.source_movie_id for candidate in shortlist),
            (
                "fixture:shared-time-loop",
                "fixture:thoughtful-space-walk",
                "fixture:quiet-investigation",
                "fixture:gentle-puzzle-box",
                "fixture:subtitled-family-mystery",
            ),
        )
        self.assertEqual(
            tuple(candidate.candidate_rank for candidate in shortlist),
            (1, 2, 3, 4, 5),
        )
        self.assertTrue(all(candidate.hard_filter_pass for candidate in shortlist))

    def test_shortlist_filters_unsafe_unwatchable_and_already_watched_titles(self) -> None:
        shortlist = fixture_candidates_to_shortlist(
            (
                FixtureCandidate(
                    source_movie_id="fixture:good-fit",
                    title="Good Fit",
                    genres=("Comedy", "Sci-Fi"),
                    provider_availability=(
                        FixtureProviderAvailability(
                            provider_name="Prime Video",
                            access_type=ProviderAccessType.FLATRATE,
                        ),
                    ),
                    original_language="en",
                    spoken_languages=("en",),
                ),
                FixtureCandidate(
                    source_movie_id="fixture:already-seen",
                    title="Already Seen",
                    genres=("Comedy", "Sci-Fi"),
                    provider_availability=(
                        FixtureProviderAvailability(
                            provider_name="Prime Video",
                            access_type=ProviderAccessType.FLATRATE,
                        ),
                    ),
                    original_language="en",
                    spoken_languages=("en",),
                    already_watched=True,
                ),
                FixtureCandidate(
                    source_movie_id="fixture:language-check",
                    title="Language Check",
                    genres=("Drama", "Sci-Fi"),
                    provider_availability=(
                        FixtureProviderAvailability(
                            provider_name="Prime Video",
                            access_type=ProviderAccessType.FLATRATE,
                        ),
                    ),
                    original_language="ja",
                    spoken_languages=("ja",),
                ),
                FixtureCandidate(
                    source_movie_id="fixture:rent-only",
                    title="Rent Only",
                    genres=("Mystery",),
                    provider_availability=(
                        FixtureProviderAvailability(
                            provider_name="Amazon Video",
                            access_type=ProviderAccessType.RENT,
                        ),
                    ),
                    original_language="en",
                    spoken_languages=("en",),
                ),
            ),
            session=DEMO_SHARED_SESSION,
            household_defaults=DEMO_HOUSEHOLD_DEFAULTS,
            users=(DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE),
        )

        self.assertEqual(
            tuple(candidate.source_movie_id for candidate in shortlist),
            ("fixture:good-fit",),
        )


if __name__ == "__main__":
    unittest.main()
