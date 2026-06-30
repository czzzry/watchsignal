from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from movie_night_mediator.storage import SQLiteSettings

CURRENT_SETUP_ID = "current"


@dataclass(frozen=True)
class SetupProfile:
    id: str
    label: str
    order: int


@dataclass(frozen=True)
class SetupDefaults:
    session_type: str
    input_mode: str
    availability_region: str
    language_access: str
    shortlist_size: int
    avoid_already_watched: bool


@dataclass(frozen=True)
class SetupState:
    household_label: str
    profiles: tuple[SetupProfile, ...]
    defaults: SetupDefaults


def default_setup_state() -> SetupState:
    return SetupState(
        household_label="Household",
        profiles=(
            SetupProfile(id="profile-1", label="Husband", order=1),
            SetupProfile(id="profile-2", label="Wife", order=2),
        ),
        defaults=SetupDefaults(
            session_type="Movie night",
            input_mode="Pass the phone",
            availability_region="Prime Video Germany",
            language_access="English audio or verified English subtitles",
            shortlist_size=5,
            avoid_already_watched=True,
        ),
    )


class SQLiteSetupStore:
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

    def load_setup(self) -> SetupState:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            setup_row = connection.execute(
                """
                SELECT
                    household_label,
                    session_type,
                    input_mode,
                    availability_region,
                    language_access,
                    shortlist_size,
                    avoid_already_watched
                FROM setup_state
                WHERE setup_id = ?
                """,
                (CURRENT_SETUP_ID,),
            ).fetchone()

            if setup_row is None:
                return default_setup_state()

            profile_rows = connection.execute(
                """
                SELECT profile_id, display_label, sort_order
                FROM setup_profiles
                WHERE setup_id = ?
                ORDER BY sort_order ASC, profile_id ASC
                """,
                (CURRENT_SETUP_ID,),
            ).fetchall()

        if len(profile_rows) < 2:
            return default_setup_state()

        return SetupState(
            household_label=setup_row["household_label"],
            profiles=tuple(
                SetupProfile(
                    id=row["profile_id"],
                    label=row["display_label"],
                    order=row["sort_order"],
                )
                for row in profile_rows
            ),
            defaults=SetupDefaults(
                session_type=setup_row["session_type"],
                input_mode=setup_row["input_mode"],
                availability_region=setup_row["availability_region"],
                language_access=setup_row["language_access"],
                shortlist_size=setup_row["shortlist_size"],
                avoid_already_watched=bool(setup_row["avoid_already_watched"]),
            ),
        )

    def save_setup(self, setup: SetupState) -> SetupState:
        if len(setup.profiles) < 2:
            raise ValueError("A setup must include at least two participant profiles.")

        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO setup_state (
                        setup_id,
                        household_label,
                        session_type,
                        input_mode,
                        availability_region,
                        language_access,
                        shortlist_size,
                        avoid_already_watched
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(setup_id) DO UPDATE SET
                        household_label = excluded.household_label,
                        session_type = excluded.session_type,
                        input_mode = excluded.input_mode,
                        availability_region = excluded.availability_region,
                        language_access = excluded.language_access,
                        shortlist_size = excluded.shortlist_size,
                        avoid_already_watched = excluded.avoid_already_watched
                    """,
                    (
                        CURRENT_SETUP_ID,
                        setup.household_label,
                        setup.defaults.session_type,
                        setup.defaults.input_mode,
                        setup.defaults.availability_region,
                        setup.defaults.language_access,
                        setup.defaults.shortlist_size,
                        int(setup.defaults.avoid_already_watched),
                    ),
                )
                connection.execute(
                    "DELETE FROM setup_profiles WHERE setup_id = ?",
                    (CURRENT_SETUP_ID,),
                )
                connection.executemany(
                    """
                    INSERT INTO setup_profiles (
                        profile_id,
                        setup_id,
                        display_label,
                        sort_order
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (
                            profile.id,
                            CURRENT_SETUP_ID,
                            profile.label,
                            profile.order,
                        )
                        for profile in setup.profiles
                    ],
                )

        return self.load_setup()

    def initialize_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS setup_state (
                        setup_id TEXT PRIMARY KEY,
                        household_label TEXT NOT NULL,
                        session_type TEXT NOT NULL,
                        input_mode TEXT NOT NULL,
                        availability_region TEXT NOT NULL,
                        language_access TEXT NOT NULL,
                        shortlist_size INTEGER NOT NULL CHECK (shortlist_size > 0),
                        avoid_already_watched INTEGER NOT NULL CHECK (
                            avoid_already_watched IN (0, 1)
                        ),
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS setup_profiles (
                        profile_id TEXT PRIMARY KEY,
                        setup_id TEXT NOT NULL REFERENCES setup_state(setup_id)
                            ON DELETE CASCADE,
                        display_label TEXT NOT NULL,
                        sort_order INTEGER NOT NULL
                    );
                    """
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
