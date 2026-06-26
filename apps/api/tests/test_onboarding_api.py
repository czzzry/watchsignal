import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.routing import APIRoute

from movie_night_mediator.api.main import (
    ParticipantOnboardingPayload,
    create_app,
)
from movie_night_mediator.app.onboarding import SQLiteOnboardingStore


GENERIC_PROFILE_ONBOARDING = {
    "profileId": "profile-a",
    "lovedTitleEntries": [
        {
            "rawTitle": "Resolved favorite",
            "status": "resolved",
            "candidate": {
                "source": "tmdb",
                "sourceId": "100",
                "title": "Resolved Favorite",
                "mediaType": "movie",
                "releaseYear": 2000,
                "overview": "Generic resolved title fixture.",
                "originalLanguage": "en",
                "popularity": 42.0,
            },
        }
    ],
    "fineTitleEntries": [
        {
            "rawTitle": "Fine plain text",
            "status": "unresolved",
            "unresolvedReason": "plain_text",
        }
    ],
    "noTitleEntries": [
        {
            "rawTitle": "No plain text",
            "status": "unresolved",
            "unresolvedReason": "plain_text",
        }
    ],
    "constraints": {
        "horrorExclusion": True,
        "subtitleIntolerance": True,
    },
    "isComplete": True,
}


class OnboardingApiTest(unittest.TestCase):
    def test_profile_onboarding_api_round_trips_resolved_and_unresolved_entries(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "onboarding.sqlite3"
            get_onboarding, put_onboarding, _ = onboarding_route_endpoints(
                create_app(
                    onboarding_store=SQLiteOnboardingStore(
                        database_path=database_path
                    )
                )
            )

            put_payload = put_onboarding(
                "profile-a",
                ParticipantOnboardingPayload(**GENERIC_PROFILE_ONBOARDING),
            )
            get_payload = get_onboarding("profile-a")

            self.assertEqual(payload_to_dict(put_payload), GENERIC_PROFILE_ONBOARDING)
            self.assertEqual(payload_to_dict(get_payload), GENERIC_PROFILE_ONBOARDING)

    def test_completion_api_locks_shared_recommendations_until_both_profiles_complete(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "onboarding.sqlite3"
            _, put_onboarding, get_completion = onboarding_route_endpoints(
                create_app(
                    onboarding_store=SQLiteOnboardingStore(
                        database_path=database_path
                    )
                )
            )

            empty_completion = get_completion(["profile-a", "profile-b"])

            self.assertTrue(empty_completion.sharedRecommendationLocked)
            self.assertEqual(
                empty_completion.incompleteProfileIds,
                ["profile-a", "profile-b"],
            )

            put_onboarding(
                "profile-a",
                ParticipantOnboardingPayload(**GENERIC_PROFILE_ONBOARDING),
            )
            partial_completion = get_completion(["profile-a", "profile-b"])

            self.assertTrue(partial_completion.sharedRecommendationLocked)
            self.assertEqual(partial_completion.completedProfileIds, ["profile-a"])
            self.assertEqual(partial_completion.incompleteProfileIds, ["profile-b"])

            put_onboarding(
                "profile-b",
                ParticipantOnboardingPayload(
                    **{
                        **GENERIC_PROFILE_ONBOARDING,
                        "profileId": "profile-b",
                    }
                ),
            )
            complete_completion = get_completion(["profile-a", "profile-b"])

            self.assertFalse(complete_completion.sharedRecommendationLocked)
            self.assertTrue(complete_completion.sharedRecommendationUnlocked)
            self.assertEqual(
                complete_completion.completedProfileIds,
                ["profile-a", "profile-b"],
            )
            self.assertEqual(complete_completion.incompleteProfileIds, [])

    def test_path_profile_id_must_match_payload_profile_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "onboarding.sqlite3"
            _, put_onboarding, _ = onboarding_route_endpoints(
                create_app(
                    onboarding_store=SQLiteOnboardingStore(
                        database_path=database_path
                    )
                )
            )

            with self.assertRaises(HTTPException):
                put_onboarding(
                    "profile-b",
                    ParticipantOnboardingPayload(**GENERIC_PROFILE_ONBOARDING),
                )


def onboarding_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return (
        routes[("GET", "/onboarding/{profile_id}")],
        routes[("PUT", "/onboarding/{profile_id}")],
        routes[("GET", "/onboarding/completion")],
    )


def payload_to_dict(payload: ParticipantOnboardingPayload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json", exclude_none=True)

    return payload.dict(exclude_none=True)


if __name__ == "__main__":
    unittest.main()
