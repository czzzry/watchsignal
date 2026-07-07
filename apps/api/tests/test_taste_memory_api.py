import tempfile
import unittest
from pathlib import Path

from fastapi.routing import APIRoute

from movie_night_mediator.api.main import (
    AppOwnedMovieWatchedPayload,
    PostWatchFeedbackPayload,
    SaveWatchlistEntryPayload,
    SessionReactionPayload,
    SubmitSessionReactionsPayload,
    TasteLabMoviePayload,
    TasteLabRatingInputPayload,
    TasteLabSubmitRatingsPayload,
    create_app,
)
from movie_night_mediator.domain import (
    SessionMode,
    SessionReactionLabel,
    SessionShortlistItem,
    SharedMovieNightSession,
    SharedSessionState,
)
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteFeedbackStore,
    SQLiteSessionStore,
    SQLiteTasteLabStore,
    SQLiteTasteMemoryStore,
    SQLiteWatchlistStore,
)
from movie_night_mediator.taste_lab import TasteLabRatingLabel


class TasteMemoryApiTest(unittest.TestCase):
    def test_profile_memory_events_capture_owned_recommendation_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "taste-memory-api.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            routes = taste_memory_route_endpoints(
                create_app(
                    backfill_store=SQLiteBackfillStore(database_path=database_path),
                    feedback_store=SQLiteFeedbackStore(database_path=database_path),
                    session_store=session_store,
                    taste_lab_store=SQLiteTasteLabStore(database_path=database_path),
                    taste_memory_store=SQLiteTasteMemoryStore(
                        database_path=database_path
                    ),
                    watchlist_store=SQLiteWatchlistStore(database_path=database_path),
                )
            )
            session_store.save_session(
                SharedMovieNightSession(
                    session_id="session-1",
                    household_id="household-1",
                    active_mode=SessionMode.COMPROMISE,
                    participant_ids=("husband", "wife"),
                    state=SharedSessionState.FOUNDER_REACTING,
                    shortlist=(
                        SessionShortlistItem("tmdb:603", "The Matrix", 1),
                        SessionShortlistItem("tmdb:680", "Pulp Fiction", 2),
                        SessionShortlistItem("tmdb:13", "Forrest Gump", 3),
                        SessionShortlistItem("tmdb:155", "The Dark Knight", 4),
                        SessionShortlistItem("tmdb:11", "Star Wars", 5),
                    ),
                )
            )

            routes["post_taste_lab_ratings"](
                profile_id="husband",
                payload=TasteLabSubmitRatingsPayload(
                    householdId="household-1",
                    ratings=[
                        TasteLabRatingInputPayload(
                            movie=TasteLabMoviePayload(
                                sourceMovieId="movielens:1",
                                title="Arrival",
                                genres=["Sci-Fi", "Drama"],
                            ),
                            label=TasteLabRatingLabel.LOVED,
                            ratedAt="2026-07-07T10:00:00Z",
                        )
                    ],
                ),
            )
            routes["post_watchlist"](
                SaveWatchlistEntryPayload(
                    householdId="household-1",
                    sourceMovieId="tmdb:603",
                    title="The Matrix",
                    savedByProfileId="husband",
                )
            )
            routes["post_app_owned_watched"](
                AppOwnedMovieWatchedPayload(
                    householdId="household-1",
                    sourceMovieId="tmdb:155",
                    title="The Dark Knight",
                    ratings=[{"profileId": "husband", "tasteLabel": "fine"}],
                )
            )
            routes["post_reactions"](
                "session-1",
                SubmitSessionReactionsPayload(
                    participantId="husband",
                    reactions=[
                        SessionReactionPayload(
                            sourceMovieId="tmdb:603",
                            reactionLabel=SessionReactionLabel.SEEN,
                        ),
                        SessionReactionPayload(
                            sourceMovieId="tmdb:680",
                            reactionLabel=SessionReactionLabel.NO,
                        ),
                        SessionReactionPayload(
                            sourceMovieId="tmdb:13",
                            reactionLabel=SessionReactionLabel.MAYBE,
                        ),
                        SessionReactionPayload(
                            sourceMovieId="tmdb:155",
                            reactionLabel=SessionReactionLabel.INTERESTED,
                        ),
                        SessionReactionPayload(
                            sourceMovieId="tmdb:11",
                            reactionLabel=SessionReactionLabel.MAYBE,
                        ),
                    ],
                ),
            )
            routes["post_feedback"](
                PostWatchFeedbackPayload(
                    householdId="household-1",
                    sessionId="session-1",
                    userId="husband",
                    sourceMovieId="tmdb:603",
                    feedbackLabel="loved",
                )
            )

            husband_events = [
                payload_to_dict(event)
                for event in routes["get_memory_events"](
                    "husband",
                    householdId="household-1",
                )
            ]
            wife_events = routes["get_memory_events"](
                "wife",
                householdId="household-1",
            )

            self.assertEqual(
                {
                    event["eventType"]
                    for event in husband_events
                },
                {
                    "taste_lab_rating",
                    "watchlist_saved",
                    "app_owned_rating",
                    "seen_before",
                    "post_watch_feedback",
                },
            )
            self.assertEqual(wife_events, [])
            self.assertTrue(
                all(event["profileId"] == "husband" for event in husband_events)
            )
            seen_event = next(
                event
                for event in husband_events
                if event["eventType"] == "seen_before"
            )
            self.assertEqual(seen_event["effectLabel"], "avoids repeats")
            taste_lab_event = next(
                event
                for event in husband_events
                if event["eventType"] == "taste_lab_rating"
            )
            self.assertEqual(taste_lab_event["genres"], ["Sci-Fi", "Drama"])
            self.assertEqual(taste_lab_event["status"], "active")


def taste_memory_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return {
        "post_taste_lab_ratings": routes[("POST", "/taste-lab/{profile_id}/ratings")],
        "post_watchlist": routes[("POST", "/watchlist")],
        "post_app_owned_watched": routes[("POST", "/app-owned-movies/watched")],
        "post_reactions": routes[("POST", "/sessions/{session_id}/reactions")],
        "post_feedback": routes[("POST", "/feedback/post-watch")],
        "get_memory_events": routes[("GET", "/profiles/{profile_id}/memory/events")],
    }


def payload_to_dict(payload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")

    return payload.dict()


if __name__ == "__main__":
    unittest.main()
