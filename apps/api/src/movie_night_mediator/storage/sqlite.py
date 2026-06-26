from __future__ import annotations

import sqlite3
from pathlib import Path

from movie_night_mediator.domain.models import (
    Household,
    HouseholdDefaults,
    HouseholdSetup,
    ParticipantProfile,
    default_household_setup,
)
from movie_night_mediator.storage.settings import SQLiteSettings


class SQLiteHouseholdStore:
    def __init__(
        self,
        database_path: str | Path | None = None,
        settings: SQLiteSettings | None = None,
    ) -> None:
        if database_path is not None and settings is not None:
            raise ValueError("Pass database_path or settings, not both.")

        if database_path is not None:
            self.database_path = Path(database_path)
        else:
            resolved_settings = settings or SQLiteSettings.from_env()
            self.database_path = resolved_settings.database_path

    def initialize_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS households (
                    household_id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    default_region TEXT NOT NULL,
                    default_service TEXT NOT NULL,
                    default_language_mode TEXT NOT NULL,
                    rewatch_avoidance_default INTEGER NOT NULL CHECK (
                        rewatch_avoidance_default IN (0, 1)
                    ),
                    active_interface TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS participant_profiles (
                    profile_id TEXT PRIMARY KEY,
                    household_id TEXT NOT NULL REFERENCES households(household_id)
                        ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    display_label TEXT NOT NULL,
                    sort_order INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (household_id, role)
                );
                """
            )

    def ensure_default_household_setup(self) -> HouseholdSetup:
        setup = default_household_setup()
        existing = self.load_household_setup(setup.household.household_id)
        if existing is not None:
            return existing

        self.save_household_setup(setup)
        return self.load_household_setup(setup.household.household_id) or setup

    def save_household_setup(self, setup: HouseholdSetup) -> None:
        if len(setup.participant_profiles) != 2:
            raise ValueError("A household setup must have exactly two participant profiles.")

        if any(
            profile.household_id != setup.household.household_id
            for profile in setup.participant_profiles
        ):
            raise ValueError("Participant profiles must belong to the setup household.")

        self.initialize_schema()
        household = setup.household
        defaults = household.defaults
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO households (
                    household_id,
                    label,
                    default_region,
                    default_service,
                    default_language_mode,
                    rewatch_avoidance_default,
                    active_interface
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(household_id) DO UPDATE SET
                    label = excluded.label,
                    default_region = excluded.default_region,
                    default_service = excluded.default_service,
                    default_language_mode = excluded.default_language_mode,
                    rewatch_avoidance_default = excluded.rewatch_avoidance_default,
                    active_interface = excluded.active_interface
                """,
                (
                    household.household_id,
                    household.label,
                    defaults.default_region,
                    defaults.default_service,
                    defaults.default_language_mode,
                    int(defaults.rewatch_avoidance_default),
                    household.active_interface,
                ),
            )
            connection.executemany(
                """
                INSERT INTO participant_profiles (
                    profile_id,
                    household_id,
                    role,
                    display_label,
                    sort_order
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    household_id = excluded.household_id,
                    role = excluded.role,
                    display_label = excluded.display_label,
                    sort_order = excluded.sort_order
                """,
                [
                    (
                        profile.profile_id,
                        profile.household_id,
                        profile.role,
                        profile.display_label,
                        profile.sort_order,
                    )
                    for profile in setup.participant_profiles
                ],
            )

    def load_household_setup(self, household_id: str) -> HouseholdSetup | None:
        self.initialize_schema()
        with self._connect() as connection:
            household_row = connection.execute(
                """
                SELECT
                    household_id,
                    label,
                    default_region,
                    default_service,
                    default_language_mode,
                    rewatch_avoidance_default,
                    active_interface
                FROM households
                WHERE household_id = ?
                """,
                (household_id,),
            ).fetchone()

            if household_row is None:
                return None

            profile_rows = connection.execute(
                """
                SELECT profile_id, household_id, role, display_label, sort_order
                FROM participant_profiles
                WHERE household_id = ?
                ORDER BY sort_order ASC, profile_id ASC
                """,
                (household_id,),
            ).fetchall()

        household = Household(
            household_id=household_row["household_id"],
            label=household_row["label"],
            defaults=HouseholdDefaults(
                default_region=household_row["default_region"],
                default_service=household_row["default_service"],
                default_language_mode=household_row["default_language_mode"],
                rewatch_avoidance_default=bool(household_row["rewatch_avoidance_default"]),
            ),
            active_interface=household_row["active_interface"],
        )
        profiles = tuple(
            ParticipantProfile(
                profile_id=row["profile_id"],
                household_id=row["household_id"],
                role=row["role"],
                display_label=row["display_label"],
                sort_order=row["sort_order"],
            )
            for row in profile_rows
        )
        return HouseholdSetup(household=household, participant_profiles=profiles)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
