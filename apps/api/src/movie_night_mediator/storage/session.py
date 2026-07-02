from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from movie_night_mediator.domain import (
    SessionMode,
    SessionReaction,
    SessionReactionLabel,
    SessionShortlistItem,
    SharedMovieNightSession,
    SharedSessionState,
)
from movie_night_mediator.storage.settings import SQLiteSettings


class SQLiteSessionStore:
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

    def save_session(
        self,
        session: SharedMovieNightSession,
    ) -> SharedMovieNightSession:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO shared_sessions (
                        session_id,
                        household_id,
                        active_mode,
                        state,
                        founder_participant_id,
                        wife_participant_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        household_id = excluded.household_id,
                        active_mode = excluded.active_mode,
                        state = excluded.state,
                        founder_participant_id = excluded.founder_participant_id,
                        wife_participant_id = excluded.wife_participant_id,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        session.session_id,
                        session.household_id,
                        session.active_mode.value,
                        session.state.value,
                        session.founder_participant_id,
                        session.wife_participant_id,
                    ),
                )
                connection.execute(
                    "DELETE FROM shared_session_shortlist WHERE session_id = ?",
                    (session.session_id,),
                )
                connection.executemany(
                    """
                    INSERT INTO shared_session_shortlist (
                        session_id,
                        source_movie_id,
                        title,
                        candidate_rank
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (
                            session.session_id,
                            item.source_movie_id,
                            item.title,
                            item.candidate_rank,
                        )
                        for item in session.shortlist
                    ],
                )
                connection.execute(
                    "DELETE FROM shared_session_previous_shortlist WHERE session_id = ?",
                    (session.session_id,),
                )
                connection.executemany(
                    """
                    INSERT INTO shared_session_previous_shortlist (
                        session_id,
                        source_movie_id,
                        title,
                        candidate_rank,
                        history_position
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            session.session_id,
                            item.source_movie_id,
                            item.title,
                            item.candidate_rank,
                            index,
                        )
                        for index, item in enumerate(
                            session.previous_shortlist,
                            start=1,
                        )
                    ],
                )
                connection.execute(
                    "DELETE FROM shared_session_reactions WHERE session_id = ?",
                    (session.session_id,),
                )
                connection.executemany(
                    """
                    INSERT INTO shared_session_reactions (
                        session_id,
                        participant_id,
                        source_movie_id,
                        reaction_label,
                        reaction_pass
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            reaction.session_id,
                            reaction.participant_id,
                            reaction.source_movie_id,
                            reaction.reaction_label.value,
                            "founder",
                        )
                        for reaction in session.founder_reactions
                    ]
                    + [
                        (
                            reaction.session_id,
                            reaction.participant_id,
                            reaction.source_movie_id,
                            reaction.reaction_label.value,
                            "wife",
                        )
                        for reaction in session.wife_reactions
                    ],
                )
                connection.execute(
                    "DELETE FROM shared_session_previous_reactions WHERE session_id = ?",
                    (session.session_id,),
                )
                connection.executemany(
                    """
                    INSERT INTO shared_session_previous_reactions (
                        session_id,
                        participant_id,
                        source_movie_id,
                        reaction_label,
                        reaction_pass,
                        history_position
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            reaction.session_id,
                            reaction.participant_id,
                            reaction.source_movie_id,
                            reaction.reaction_label.value,
                            "founder",
                            index,
                        )
                        for index, reaction in enumerate(
                            session.previous_founder_reactions,
                            start=1,
                        )
                    ]
                    + [
                        (
                            reaction.session_id,
                            reaction.participant_id,
                            reaction.source_movie_id,
                            reaction.reaction_label.value,
                            "wife",
                            index,
                        )
                        for index, reaction in enumerate(
                            session.previous_wife_reactions,
                            start=1,
                        )
                    ],
                )
                connection.execute(
                    "DELETE FROM shared_session_reranks WHERE session_id = ?",
                    (session.session_id,),
                )
                connection.executemany(
                    """
                    INSERT INTO shared_session_reranks (
                        session_id,
                        source_movie_id,
                        rerank_position
                    )
                    VALUES (?, ?, ?)
                    """,
                    [
                        (session.session_id, source_movie_id, index)
                        for index, source_movie_id in enumerate(
                            session.reranked_source_movie_ids,
                            start=1,
                        )
                    ],
                )

        loaded = self.load_session(session.session_id)
        if loaded is None:
            raise RuntimeError("Saved shared session could not be reloaded.")
        return loaded

    def load_session(self, session_id: str) -> SharedMovieNightSession | None:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            session_row = connection.execute(
                """
                SELECT
                    session_id,
                    household_id,
                    active_mode,
                    state,
                    founder_participant_id,
                    wife_participant_id
                FROM shared_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

            if session_row is None:
                return None

            shortlist_rows = connection.execute(
                """
                SELECT source_movie_id, title, candidate_rank
                FROM shared_session_shortlist
                WHERE session_id = ?
                ORDER BY candidate_rank ASC, source_movie_id ASC
                """,
                (session_id,),
            ).fetchall()
            reaction_rows = connection.execute(
                """
                SELECT participant_id, source_movie_id, reaction_label, reaction_pass
                FROM shared_session_reactions
                WHERE session_id = ?
                ORDER BY reaction_pass ASC, source_movie_id ASC
                """,
                (session_id,),
            ).fetchall()
            previous_shortlist_rows = connection.execute(
                """
                SELECT source_movie_id, title, candidate_rank
                FROM shared_session_previous_shortlist
                WHERE session_id = ?
                ORDER BY history_position ASC
                """,
                (session_id,),
            ).fetchall()
            previous_reaction_rows = connection.execute(
                """
                SELECT participant_id, source_movie_id, reaction_label, reaction_pass
                FROM shared_session_previous_reactions
                WHERE session_id = ?
                ORDER BY reaction_pass ASC, history_position ASC
                """,
                (session_id,),
            ).fetchall()
            rerank_rows = connection.execute(
                """
                SELECT source_movie_id
                FROM shared_session_reranks
                WHERE session_id = ?
                ORDER BY rerank_position ASC
                """,
                (session_id,),
            ).fetchall()

        founder_reactions = []
        wife_reactions = []
        for row in reaction_rows:
            reaction = SessionReaction(
                session_id=session_row["session_id"],
                participant_id=row["participant_id"],
                source_movie_id=row["source_movie_id"],
                reaction_label=SessionReactionLabel(row["reaction_label"]),
            )
            if row["reaction_pass"] == "founder":
                founder_reactions.append(reaction)
            else:
                wife_reactions.append(reaction)

        previous_founder_reactions = []
        previous_wife_reactions = []
        for row in previous_reaction_rows:
            reaction = SessionReaction(
                session_id=session_row["session_id"],
                participant_id=row["participant_id"],
                source_movie_id=row["source_movie_id"],
                reaction_label=SessionReactionLabel(row["reaction_label"]),
            )
            if row["reaction_pass"] == "founder":
                previous_founder_reactions.append(reaction)
            else:
                previous_wife_reactions.append(reaction)

        return SharedMovieNightSession(
            session_id=session_row["session_id"],
            household_id=session_row["household_id"],
            active_mode=SessionMode(session_row["active_mode"]),
            state=SharedSessionState(session_row["state"]),
            participant_ids=(
                session_row["founder_participant_id"],
                session_row["wife_participant_id"],
            ),
            shortlist=tuple(
                SessionShortlistItem(
                    source_movie_id=row["source_movie_id"],
                    title=row["title"],
                    candidate_rank=row["candidate_rank"],
                )
                for row in shortlist_rows
            ),
            founder_reactions=tuple(founder_reactions),
            wife_reactions=tuple(wife_reactions),
            reranked_source_movie_ids=tuple(
                row["source_movie_id"] for row in rerank_rows
            ),
            previous_shortlist=tuple(
                SessionShortlistItem(
                    source_movie_id=row["source_movie_id"],
                    title=row["title"],
                    candidate_rank=row["candidate_rank"],
                )
                for row in previous_shortlist_rows
            ),
            previous_founder_reactions=tuple(previous_founder_reactions),
            previous_wife_reactions=tuple(previous_wife_reactions),
        )

    def list_sessions(
        self,
        *,
        household_id: str,
        limit: int = 10,
    ) -> tuple[SharedMovieNightSession, ...]:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT session_id
                FROM shared_sessions
                WHERE household_id = ?
                ORDER BY updated_at DESC, session_id DESC
                LIMIT ?
                """,
                (household_id, limit),
            ).fetchall()

        sessions = []
        for row in rows:
            session = self.load_session(row["session_id"])
            if session is not None:
                sessions.append(session)

        return tuple(sessions)

    def initialize_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS shared_sessions (
                        session_id TEXT PRIMARY KEY,
                        household_id TEXT NOT NULL,
                        active_mode TEXT NOT NULL CHECK (
                            active_mode IN (
                                'husband_first',
                                'wife_first',
                                'compromise'
                            )
                        ),
                        state TEXT NOT NULL CHECK (
                            state IN (
                                'founder_reacting',
                                'handoff',
                                'wife_reacting',
                                'reranked'
                            )
                        ),
                        founder_participant_id TEXT NOT NULL,
                        wife_participant_id TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS shared_session_shortlist (
                        session_id TEXT NOT NULL REFERENCES shared_sessions(session_id)
                            ON DELETE CASCADE,
                        source_movie_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        candidate_rank INTEGER NOT NULL,
                        PRIMARY KEY (session_id, source_movie_id)
                    );

                    CREATE TABLE IF NOT EXISTS shared_session_reactions (
                        session_id TEXT NOT NULL REFERENCES shared_sessions(session_id)
                            ON DELETE CASCADE,
                        participant_id TEXT NOT NULL,
                        source_movie_id TEXT NOT NULL,
                        reaction_label TEXT NOT NULL CHECK (
                            reaction_label IN ('interested', 'maybe', 'no', 'seen')
                        ),
                        reaction_pass TEXT NOT NULL CHECK (
                            reaction_pass IN ('founder', 'wife')
                        ),
                        PRIMARY KEY (session_id, participant_id, source_movie_id)
                    );

                    CREATE TABLE IF NOT EXISTS shared_session_previous_shortlist (
                        session_id TEXT NOT NULL REFERENCES shared_sessions(session_id)
                            ON DELETE CASCADE,
                        source_movie_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        candidate_rank INTEGER NOT NULL,
                        history_position INTEGER NOT NULL,
                        PRIMARY KEY (session_id, source_movie_id)
                    );

                    CREATE TABLE IF NOT EXISTS shared_session_previous_reactions (
                        session_id TEXT NOT NULL REFERENCES shared_sessions(session_id)
                            ON DELETE CASCADE,
                        participant_id TEXT NOT NULL,
                        source_movie_id TEXT NOT NULL,
                        reaction_label TEXT NOT NULL CHECK (
                            reaction_label IN ('interested', 'maybe', 'no', 'seen')
                        ),
                        reaction_pass TEXT NOT NULL CHECK (
                            reaction_pass IN ('founder', 'wife')
                        ),
                        history_position INTEGER NOT NULL,
                        PRIMARY KEY (
                            session_id,
                            participant_id,
                            source_movie_id
                        )
                    );

                    CREATE TABLE IF NOT EXISTS shared_session_reranks (
                        session_id TEXT NOT NULL REFERENCES shared_sessions(session_id)
                            ON DELETE CASCADE,
                        source_movie_id TEXT NOT NULL,
                        rerank_position INTEGER NOT NULL,
                        PRIMARY KEY (session_id, source_movie_id)
                    );
                    """
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
