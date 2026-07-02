import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.app.session import (
    SessionTransitionError,
    SharedSessionService,
)
from movie_night_mediator.domain import (
    OnboardingConstraints,
    ParticipantOnboarding,
    SessionMode,
    SessionReaction,
    SessionReactionLabel,
    SessionShortlistItem,
    SharedSessionState,
    TitleResolutionEntry,
)
from movie_night_mediator.storage import SQLiteSessionStore


class SharedSessionServiceTest(unittest.TestCase):
    def test_session_moves_through_pass_the_phone_flow_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            service = create_service_with_complete_onboarding(database_path)

            session = service.start_session(
                session_id="session-1",
                active_mode=SessionMode.COMPROMISE,
                participant_ids=("husband", "wife"),
                shortlist=GENERIC_SHORTLIST,
            )

            self.assertEqual(session.state, SharedSessionState.FOUNDER_REACTING)

            after_founder = service.submit_reactions(
                "session-1",
                "husband",
                reactions_for("session-1", "husband", ["maybe", "interested", "no", "seen", "maybe"]),
            )

            self.assertEqual(after_founder.state, SharedSessionState.HANDOFF)
            self.assertEqual(len(after_founder.founder_reactions), 5)

            after_handoff = service.advance_handoff("session-1")

            self.assertEqual(after_handoff.state, SharedSessionState.WIFE_REACTING)

            after_wife = service.submit_reactions(
                "session-1",
                "wife",
                reactions_for("session-1", "wife", ["interested", "maybe", "no", "seen", "interested"]),
            )

            self.assertEqual(after_wife.state, SharedSessionState.RERANKED)
            self.assertEqual(after_wife.best_pick_source_movie_id, "tmdb:1")
            self.assertEqual(after_wife.reranked_source_movie_ids[-1], "tmdb:4")

            reloaded = service.load_session("session-1")

            assert reloaded is not None
            self.assertEqual(reloaded.state, SharedSessionState.RERANKED)
            self.assertEqual(reloaded.reranked_source_movie_ids, after_wife.reranked_source_movie_ids)
            self.assertEqual(len(reloaded.wife_reactions), 5)

    def test_start_requires_completed_onboarding_for_both_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            service = SharedSessionService(
                session_store=SQLiteSessionStore(database_path=database_path),
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
            )

            with self.assertRaisesRegex(ValueError, "completed onboarding"):
                service.start_session(
                    session_id="session-1",
                    participant_ids=("husband", "wife"),
                    shortlist=GENERIC_SHORTLIST,
                )

    def test_invalid_transition_rejects_second_participant_before_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            service = create_service_with_complete_onboarding(database_path)
            service.start_session(
                session_id="session-1",
                participant_ids=("husband", "wife"),
                shortlist=GENERIC_SHORTLIST,
            )

            with self.assertRaisesRegex(SessionTransitionError, "Founder reaction pass"):
                service.submit_reactions(
                    "session-1",
                    "wife",
                    reactions_for("session-1", "wife", ["maybe", "maybe", "maybe", "maybe", "maybe"]),
                )

    def test_reranked_session_cannot_change_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            service = create_service_with_complete_onboarding(database_path)
            service.start_session(
                session_id="session-1",
                participant_ids=("husband", "wife"),
                shortlist=GENERIC_SHORTLIST,
            )
            service.submit_reactions(
                "session-1",
                "husband",
                reactions_for("session-1", "husband", ["maybe", "maybe", "maybe", "maybe", "maybe"]),
            )
            service.advance_handoff("session-1")
            service.submit_reactions(
                "session-1",
                "wife",
                reactions_for("session-1", "wife", ["maybe", "maybe", "maybe", "maybe", "maybe"]),
            )

            with self.assertRaisesRegex(SessionTransitionError, "cannot change mode"):
                service.update_mode("session-1", SessionMode.WIFE_FIRST)

    def test_continue_with_shortlist_preserves_prior_batch_and_reactions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            service = create_service_with_complete_onboarding(database_path)
            service.start_session(
                session_id="session-1",
                participant_ids=("husband", "wife"),
                shortlist=GENERIC_SHORTLIST,
            )
            service.submit_reactions(
                "session-1",
                "husband",
                reactions_for("session-1", "husband", ["maybe", "interested", "no", "seen", "maybe"]),
            )
            service.advance_handoff("session-1")
            service.submit_reactions(
                "session-1",
                "wife",
                reactions_for("session-1", "wife", ["interested", "maybe", "no", "seen", "interested"]),
            )

            continued = service.continue_with_shortlist(
                "session-1",
                CONTINUATION_SHORTLIST,
            )
            reloaded = service.load_session("session-1")

            self.assertEqual(continued.state, SharedSessionState.FOUNDER_REACTING)
            self.assertEqual(continued.shortlist, CONTINUATION_SHORTLIST)
            self.assertEqual(continued.previous_shortlist, GENERIC_SHORTLIST)
            self.assertEqual(len(continued.previous_founder_reactions), 5)
            self.assertEqual(len(continued.previous_wife_reactions), 5)
            self.assertEqual(continued.founder_reactions, ())
            self.assertEqual(continued.wife_reactions, ())
            self.assertEqual(continued.batch_count, 2)
            self.assertEqual(
                continued.shown_source_movie_ids,
                (
                    "tmdb:1",
                    "tmdb:2",
                    "tmdb:3",
                    "tmdb:4",
                    "tmdb:5",
                    "tmdb:6",
                    "tmdb:7",
                    "tmdb:8",
                    "tmdb:9",
                    "tmdb:10",
                ),
            )
            assert reloaded is not None
            self.assertEqual(reloaded.previous_shortlist, GENERIC_SHORTLIST)
            self.assertEqual(len(reloaded.previous_founder_reactions), 5)

    def test_continue_rejects_already_shown_movies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            service = create_service_with_complete_onboarding(database_path)
            service.start_session(
                session_id="session-1",
                participant_ids=("husband", "wife"),
                shortlist=GENERIC_SHORTLIST,
            )
            service.submit_reactions(
                "session-1",
                "husband",
                reactions_for("session-1", "husband", ["maybe", "maybe", "maybe", "maybe", "maybe"]),
            )
            service.advance_handoff("session-1")
            service.submit_reactions(
                "session-1",
                "wife",
                reactions_for("session-1", "wife", ["maybe", "maybe", "maybe", "maybe", "maybe"]),
            )

            with self.assertRaisesRegex(ValueError, "already-shown"):
                service.continue_with_shortlist(
                    "session-1",
                    (
                        SessionShortlistItem("tmdb:1", "Duplicate Pick", 1),
                        *CONTINUATION_SHORTLIST[:4],
                    ),
                )


GENERIC_SHORTLIST = (
    SessionShortlistItem("tmdb:1", "First Pick", 1),
    SessionShortlistItem("tmdb:2", "Second Pick", 2),
    SessionShortlistItem("tmdb:3", "Third Pick", 3),
    SessionShortlistItem("tmdb:4", "Fourth Pick", 4),
    SessionShortlistItem("tmdb:5", "Fifth Pick", 5),
)

CONTINUATION_SHORTLIST = (
    SessionShortlistItem("tmdb:6", "Sixth Pick", 1),
    SessionShortlistItem("tmdb:7", "Seventh Pick", 2),
    SessionShortlistItem("tmdb:8", "Eighth Pick", 3),
    SessionShortlistItem("tmdb:9", "Ninth Pick", 4),
    SessionShortlistItem("tmdb:10", "Tenth Pick", 5),
)


def create_service_with_complete_onboarding(database_path: Path) -> SharedSessionService:
    onboarding_store = SQLiteOnboardingStore(database_path=database_path)
    for profile_id in ("husband", "wife"):
        onboarding_store.save_profile_onboarding(complete_onboarding(profile_id))

    return SharedSessionService(
        session_store=SQLiteSessionStore(database_path=database_path),
        onboarding_store=onboarding_store,
    )


def complete_onboarding(profile_id: str) -> ParticipantOnboarding:
    return ParticipantOnboarding(
        profile_id=profile_id,
        loved_title_entries=(TitleResolutionEntry.unresolved("Loved seed"),),
        fine_title_entries=(TitleResolutionEntry.unresolved("Fine seed"),),
        no_title_entries=(TitleResolutionEntry.unresolved("No seed"),),
        constraints=OnboardingConstraints(),
    )


def reactions_for(
    session_id: str,
    participant_id: str,
    labels: list[str],
) -> tuple[SessionReaction, ...]:
    return tuple(
        SessionReaction(
            session_id=session_id,
            participant_id=participant_id,
            source_movie_id=item.source_movie_id,
            reaction_label=SessionReactionLabel(label),
        )
        for item, label in zip(GENERIC_SHORTLIST, labels, strict=True)
    )


if __name__ == "__main__":
    unittest.main()
