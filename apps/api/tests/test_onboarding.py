import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.domain import (
    MediaType,
    OnboardingConstraints,
    ParticipantOnboarding,
    TitleResolutionCandidate,
    TitleResolutionEntry,
    TitleResolutionStatus,
)


class SQLiteOnboardingStoreTest(unittest.TestCase):
    def test_profile_onboarding_survives_sqlite_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "onboarding.sqlite3"
            store = SQLiteOnboardingStore(database_path=database_path)
            resolved_candidate = TitleResolutionCandidate(
                source="tmdb",
                source_id="603",
                title="The Matrix",
                media_type=MediaType.MOVIE,
                release_year=1999,
                overview="A test fixture candidate.",
                original_language="en",
                popularity=83.1,
            )
            onboarding = ParticipantOnboarding(
                profile_id="profile-a",
                loved_title_entries=(
                    TitleResolutionEntry.resolved(
                        "Matrix",
                        resolved_candidate,
                    ),
                ),
                fine_title_entries=(
                    TitleResolutionEntry.unresolved(
                        "Gentle space movie",
                        reason="no_match",
                    ),
                ),
                no_title_entries=(
                    TitleResolutionEntry.unresolved(
                        "Too intense example",
                        reason="plain_text",
                    ),
                ),
                constraints=OnboardingConstraints(
                    horror_exclusion=True,
                    subtitle_intolerance=True,
                ),
            )

            saved_onboarding = store.save_profile_onboarding(onboarding)
            loaded_onboarding = SQLiteOnboardingStore(
                database_path=database_path
            ).load_profile_onboarding("profile-a")

            self.assertEqual(saved_onboarding, onboarding)
            self.assertEqual(loaded_onboarding, onboarding)
            self.assertTrue(loaded_onboarding.is_complete)
            self.assertTrue(loaded_onboarding.constraints.horror_exclusion)
            self.assertTrue(loaded_onboarding.constraints.subtitle_intolerance)
            self.assertEqual(
                loaded_onboarding.loved_title_entries[0].status,
                TitleResolutionStatus.RESOLVED,
            )
            self.assertEqual(
                loaded_onboarding.loved_title_entries[0].candidate.source_movie_id,
                "tmdb:603",
            )
            self.assertEqual(
                loaded_onboarding.fine_title_entries[0].status,
                TitleResolutionStatus.UNRESOLVED,
            )

    def test_shared_recommendations_stay_locked_until_both_profiles_complete(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "onboarding.sqlite3"
            store = SQLiteOnboardingStore(database_path=database_path)
            required_profile_ids = ("profile-a", "profile-b")

            empty_completion = store.load_completion(required_profile_ids)

            self.assertTrue(empty_completion.shared_recommendation_locked)
            self.assertEqual(
                empty_completion.incomplete_profile_ids,
                required_profile_ids,
            )

            store.save_profile_onboarding(
                _complete_profile_onboarding(profile_id="profile-a")
            )
            partial_completion = store.load_completion(required_profile_ids)

            self.assertTrue(partial_completion.shared_recommendation_locked)
            self.assertEqual(
                partial_completion.completed_profile_ids,
                ("profile-a",),
            )
            self.assertEqual(
                partial_completion.incomplete_profile_ids,
                ("profile-b",),
            )

            store.save_profile_onboarding(
                _complete_profile_onboarding(profile_id="profile-b")
            )
            complete_onboarding = store.load_completion(required_profile_ids)

            self.assertFalse(complete_onboarding.shared_recommendation_locked)
            self.assertTrue(complete_onboarding.shared_recommendation_unlocked)
            self.assertEqual(
                complete_onboarding.completed_profile_ids,
                required_profile_ids,
            )
            self.assertEqual(complete_onboarding.incomplete_profile_ids, ())

    def test_profile_requires_loved_fine_and_no_seed_titles_to_be_complete(self) -> None:
        onboarding = ParticipantOnboarding(
            profile_id="profile-a",
            loved_title_entries=(TitleResolutionEntry.unresolved("Loved example"),),
            fine_title_entries=(TitleResolutionEntry.unresolved("Fine example"),),
        )

        self.assertFalse(onboarding.is_complete)


def _complete_profile_onboarding(profile_id: str) -> ParticipantOnboarding:
    return ParticipantOnboarding(
        profile_id=profile_id,
        loved_title_entries=(TitleResolutionEntry.unresolved("Loved example"),),
        fine_title_entries=(TitleResolutionEntry.unresolved("Fine example"),),
        no_title_entries=(TitleResolutionEntry.unresolved("No example"),),
    )


if __name__ == "__main__":
    unittest.main()
