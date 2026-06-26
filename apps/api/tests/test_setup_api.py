import tempfile
import unittest
from pathlib import Path

from fastapi.routing import APIRoute

from movie_night_mediator.api.main import SetupStatePayload, create_app
from movie_night_mediator.app.setup import SQLiteSetupStore


GENERIC_UPDATED_SETUP = {
    "householdLabel": "Household",
    "profiles": [
        {"id": "profile-1", "label": "Viewer A", "order": 1},
        {"id": "profile-2", "label": "Viewer B", "order": 2},
    ],
    "defaults": {
        "sessionType": "Movie night",
        "inputMode": "Pass the phone",
        "availabilityRegion": "Library region",
        "languageAccess": "Original audio with verified subtitles",
        "shortlistSize": 4,
        "avoidAlreadyWatched": False,
    },
}


class SetupApiTest(unittest.TestCase):
    def test_get_setup_returns_generic_defaults_when_nothing_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "setup.sqlite3"
            get_setup, _ = setup_route_endpoints(
                create_app(setup_store=SQLiteSetupStore(database_path=database_path))
            )

            payload = get_setup()

            self.assertEqual(
                payload_to_dict(payload),
                {
                    "householdLabel": "Household",
                    "profiles": [
                        {"id": "profile-1", "label": "Husband", "order": 1},
                        {"id": "profile-2", "label": "Wife", "order": 2},
                    ],
                    "defaults": {
                        "sessionType": "Movie night",
                        "inputMode": "Pass the phone",
                        "availabilityRegion": "Prime Video Germany",
                        "languageAccess": (
                            "English audio or verified English subtitles"
                        ),
                        "shortlistSize": 5,
                        "avoidAlreadyWatched": True,
                    },
                },
            )

    def test_put_setup_persists_updated_setup_for_later_get(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "setup.sqlite3"
            get_setup, put_setup = setup_route_endpoints(
                create_app(setup_store=SQLiteSetupStore(database_path=database_path))
            )

            put_payload = put_setup(SetupStatePayload(**GENERIC_UPDATED_SETUP))
            get_payload = get_setup()

            self.assertEqual(payload_to_dict(put_payload), GENERIC_UPDATED_SETUP)
            self.assertEqual(payload_to_dict(get_payload), GENERIC_UPDATED_SETUP)

    def test_api_write_survives_sqlite_service_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "setup.sqlite3"
            _, put_setup = setup_route_endpoints(
                create_app(setup_store=SQLiteSetupStore(database_path=database_path))
            )

            response = put_setup(SetupStatePayload(**GENERIC_UPDATED_SETUP))
            loaded_setup = SQLiteSetupStore(database_path=database_path).load_setup()

            self.assertEqual(payload_to_dict(response), GENERIC_UPDATED_SETUP)
            self.assertEqual(loaded_setup.household_label, "Household")
            self.assertEqual(
                [profile.label for profile in loaded_setup.profiles],
                ["Viewer A", "Viewer B"],
            )
            self.assertEqual(
                loaded_setup.defaults.availability_region,
                "Library region",
            )
            self.assertEqual(loaded_setup.defaults.shortlist_size, 4)
            self.assertFalse(loaded_setup.defaults.avoid_already_watched)


def setup_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return routes[("GET", "/setup")], routes[("PUT", "/setup")]


def payload_to_dict(payload: SetupStatePayload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")

    return payload.dict()


if __name__ == "__main__":
    unittest.main()
