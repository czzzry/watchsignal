from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from movie_night_mediator.storage import SQLiteSettings

CURRENT_SETUP_ID = "current"
TESTER_PROFILE_ID = "cezary-tester"
TESTER_PROFILE_LABEL = "Cezary - tester"
TESTER_PROFILE_AVATAR_KEY = "comet"
TESTER_PROFILE_COLOR_KEY = "amber"


@dataclass(frozen=True)
class SetupProfile:
    id: str
    label: str
    order: int
    avatar_key: str
    color_key: str


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
            SetupProfile(
                id="profile-1",
                label="Husband",
                order=1,
                avatar_key="spark",
                color_key="cyan",
            ),
            SetupProfile(
                id="profile-2",
                label="Wife",
                order=2,
                avatar_key="moon",
                color_key="rose",
            ),
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
                SELECT profile_id, display_label, sort_order, avatar_key, color_key
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
                    avatar_key=row["avatar_key"],
                    color_key=row["color_key"],
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
                        sort_order,
                        avatar_key,
                        color_key
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            profile.id,
                            CURRENT_SETUP_ID,
                            profile.label,
                            profile.order,
                            profile.avatar_key,
                            profile.color_key,
                        )
                        for profile in setup.profiles
                    ],
                )

        return self.load_setup()

    def ensure_tester_profile(self) -> SetupState:
        setup = self.load_setup()
        existing_profile_ids = {profile.id for profile in setup.profiles}
        if TESTER_PROFILE_ID in existing_profile_ids:
            return setup

        next_order = max(profile.order for profile in setup.profiles) + 1
        return self.save_setup(
            SetupState(
                household_label=setup.household_label,
                profiles=(
                    *setup.profiles,
                    SetupProfile(
                        id=TESTER_PROFILE_ID,
                        label=TESTER_PROFILE_LABEL,
                        order=next_order,
                        avatar_key=TESTER_PROFILE_AVATAR_KEY,
                        color_key=TESTER_PROFILE_COLOR_KEY,
                    ),
                ),
                defaults=setup.defaults,
            )
        )

    def rename_profile(self, profile_id: str, display_label: str) -> SetupState:
        normalized_profile_id = profile_id.strip()
        normalized_display_label = display_label.strip()
        if not normalized_profile_id:
            raise ValueError("Profile rename requires a profile id.")
        if not normalized_display_label:
            raise ValueError("Profile rename requires a display label.")

        setup = self.load_setup()
        renamed_profiles = tuple(
            SetupProfile(
                id=profile.id,
                label=(
                    normalized_display_label
                    if profile.id == normalized_profile_id
                    else profile.label
                ),
                order=profile.order,
                avatar_key=profile.avatar_key,
                color_key=profile.color_key,
            )
            for profile in setup.profiles
        )

        if renamed_profiles == setup.profiles:
            raise LookupError("Profile not found.")

        return self.save_setup(
            SetupState(
                household_label=setup.household_label,
                profiles=renamed_profiles,
                defaults=setup.defaults,
            )
        )

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
                        sort_order INTEGER NOT NULL,
                        avatar_key TEXT NOT NULL DEFAULT 'spark',
                        color_key TEXT NOT NULL DEFAULT 'cyan'
                    );
                    """
                )
                columns = {
                    row["name"]
                    for row in connection.execute("PRAGMA table_info(setup_profiles)")
                }
                added_avatar_key = False
                added_color_key = False
                if "avatar_key" not in columns:
                    connection.execute(
                        "ALTER TABLE setup_profiles ADD COLUMN avatar_key TEXT NOT NULL DEFAULT 'spark'"
                    )
                    added_avatar_key = True
                if "color_key" not in columns:
                    connection.execute(
                        "ALTER TABLE setup_profiles ADD COLUMN color_key TEXT NOT NULL DEFAULT 'cyan'"
                    )
                    added_color_key = True
                if added_avatar_key:
                    connection.execute(
                        """
                        UPDATE setup_profiles
                        SET avatar_key = 'moon'
                        WHERE sort_order = 2
                        """
                    )
                if added_color_key:
                    connection.execute(
                        """
                        UPDATE setup_profiles
                        SET color_key = 'rose'
                        WHERE sort_order = 2
                        """
                    )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
