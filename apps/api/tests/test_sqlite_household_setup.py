import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from movie_night_mediator.domain import (
    Household,
    HouseholdDefaults,
    HouseholdSetup,
    ParticipantProfile,
)
from movie_night_mediator.storage import (
    SQLITE_PATH_ENV_VAR,
    SQLiteHouseholdStore,
    SQLiteSettings,
)


class SQLiteHouseholdSetupTest(unittest.TestCase):
    def test_database_path_can_come_from_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "local-household.sqlite3"
            with patch.dict(
                "os.environ",
                {SQLITE_PATH_ENV_VAR: str(database_path)},
                clear=False,
            ):
                settings = SQLiteSettings.from_env()

            self.assertEqual(settings.database_path, database_path)

    def test_default_household_setup_survives_sqlite_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "household.sqlite3"
            first_store = SQLiteHouseholdStore(database_path=database_path)

            created_setup = first_store.ensure_default_household_setup()

            second_store = SQLiteHouseholdStore(database_path=database_path)
            loaded_setup = second_store.load_household_setup(
                created_setup.household.household_id
            )

            self.assertIsNotNone(loaded_setup)
            assert loaded_setup is not None
            self.assertEqual(loaded_setup.household.label, "Household")
            self.assertEqual(
                loaded_setup.household.defaults,
                HouseholdDefaults(),
            )
            self.assertEqual(
                [profile.display_label for profile in loaded_setup.participant_profiles],
                ["Husband", "Wife"],
            )

    def test_two_generic_participant_profiles_survive_sqlite_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "household.sqlite3"
            setup = HouseholdSetup(
                household=Household(
                    household_id="generic-household",
                    label="Household",
                    defaults=HouseholdDefaults(
                        default_region="DE",
                        default_service="Prime Video",
                        default_language_mode="english_or_english_subtitles",
                        rewatch_avoidance_default=True,
                    ),
                ),
                participant_profiles=(
                    ParticipantProfile(
                        profile_id="generic-husband",
                        household_id="generic-household",
                        role="husband",
                        display_label="Husband",
                        sort_order=1,
                    ),
                    ParticipantProfile(
                        profile_id="generic-wife",
                        household_id="generic-household",
                        role="wife",
                        display_label="Wife",
                        sort_order=2,
                    ),
                ),
            )
            first_store = SQLiteHouseholdStore(database_path=database_path)

            first_store.save_household_setup(setup)

            second_store = SQLiteHouseholdStore(database_path=database_path)
            loaded_setup = second_store.load_household_setup("generic-household")

            self.assertEqual(loaded_setup, setup)


if __name__ == "__main__":
    unittest.main()

