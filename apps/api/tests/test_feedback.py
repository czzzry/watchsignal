import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.app.feedback import PostWatchFeedbackService
from movie_night_mediator.domain import DEFAULT_HOUSEHOLD_ID
from movie_night_mediator.storage import SQLiteFeedbackStore


class PostWatchFeedbackServiceTest(unittest.TestCase):
    def test_feedback_survives_sqlite_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "feedback.sqlite3"
            service = PostWatchFeedbackService(
                store=SQLiteFeedbackStore(database_path=database_path)
            )

            saved_feedback = service.save_feedback(
                household_id=DEFAULT_HOUSEHOLD_ID,
                session_id="session-1",
                user_id="profile-1",
                source_movie_id="tmdb:603",
                feedback_label="Loved",
                free_text_note=" Still plays well. ",
            )
            loaded_feedback = PostWatchFeedbackService(
                store=SQLiteFeedbackStore(database_path=database_path)
            ).list_feedback(
                household_id=DEFAULT_HOUSEHOLD_ID,
                session_id="session-1",
            )

            self.assertEqual(saved_feedback.feedback_label, "loved")
            self.assertEqual(saved_feedback.free_text_note, "Still plays well.")
            self.assertEqual(loaded_feedback, (saved_feedback,))

    def test_feedback_can_be_listed_for_whole_household(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = PostWatchFeedbackService(
                store=SQLiteFeedbackStore(
                    database_path=Path(directory) / "feedback.sqlite3"
                )
            )

            service.save_feedback(
                household_id=DEFAULT_HOUSEHOLD_ID,
                session_id="session-1",
                user_id="profile-1",
                source_movie_id="tmdb:603",
                feedback_label="fine",
            )
            service.save_feedback(
                household_id=DEFAULT_HOUSEHOLD_ID,
                session_id="session-2",
                user_id="profile-2",
                source_movie_id="tmdb:13",
                feedback_label="no",
                free_text_note="Not tonight.",
            )

            loaded_feedback = service.list_feedback(
                household_id=DEFAULT_HOUSEHOLD_ID,
            )

            self.assertEqual(len(loaded_feedback), 2)
            self.assertEqual(
                {feedback.session_id for feedback in loaded_feedback},
                {"session-1", "session-2"},
            )

    def test_duplicate_feedback_updates_existing_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = PostWatchFeedbackService(
                store=SQLiteFeedbackStore(
                    database_path=Path(directory) / "feedback.sqlite3"
                )
            )

            service.save_feedback(
                household_id=DEFAULT_HOUSEHOLD_ID,
                session_id="session-1",
                user_id="profile-1",
                source_movie_id="tmdb:603",
                feedback_label="fine",
            )
            updated_feedback = service.save_feedback(
                household_id=DEFAULT_HOUSEHOLD_ID,
                session_id="session-1",
                user_id="profile-1",
                source_movie_id="tmdb:603",
                feedback_label="loved",
                free_text_note="Changed my mind.",
            )

            loaded_feedback = service.list_feedback(
                household_id=DEFAULT_HOUSEHOLD_ID,
                session_id="session-1",
            )

            self.assertEqual(loaded_feedback, (updated_feedback,))
            self.assertEqual(loaded_feedback[0].feedback_label, "loved")
            self.assertEqual(loaded_feedback[0].free_text_note, "Changed my mind.")

    def test_feedback_rejects_empty_ids_and_unknown_labels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = PostWatchFeedbackService(
                store=SQLiteFeedbackStore(
                    database_path=Path(directory) / "feedback.sqlite3"
                )
            )

            with self.assertRaises(ValueError):
                service.save_feedback(
                    household_id=DEFAULT_HOUSEHOLD_ID,
                    session_id=" ",
                    user_id="profile-1",
                    source_movie_id="tmdb:603",
                    feedback_label="loved",
                )

            with self.assertRaises(ValueError):
                service.save_feedback(
                    household_id=DEFAULT_HOUSEHOLD_ID,
                    session_id="session-1",
                    user_id="profile-1",
                    source_movie_id="tmdb:603",
                    feedback_label="five stars",
                )


if __name__ == "__main__":
    unittest.main()
