from __future__ import annotations

from uuid import uuid4

from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.domain import (
    DEFAULT_HOUSEHOLD_ID,
    SessionMode,
    SessionReaction,
    SessionReactionLabel,
    SessionShortlistItem,
    SharedMovieNightSession,
    SharedSessionState,
)
from movie_night_mediator.storage import SQLiteSessionStore


class SessionTransitionError(ValueError):
    pass


class SharedSessionService:
    def __init__(
        self,
        session_store: SQLiteSessionStore,
        onboarding_store: SQLiteOnboardingStore,
    ) -> None:
        self.session_store = session_store
        self.onboarding_store = onboarding_store

    def start_session(
        self,
        *,
        household_id: str = DEFAULT_HOUSEHOLD_ID,
        active_mode: SessionMode = SessionMode.COMPROMISE,
        participant_ids: tuple[str, str],
        shortlist: tuple[SessionShortlistItem, ...],
        session_id: str | None = None,
    ) -> SharedMovieNightSession:
        if len(shortlist) != 5:
            raise ValueError("Shared sessions require a five-title shortlist.")

        if len({item.source_movie_id for item in shortlist}) != len(shortlist):
            raise ValueError("Shortlist source movie ids must be unique.")

        completion = self.onboarding_store.load_completion(participant_ids)
        if completion.shared_recommendation_locked:
            raise ValueError("Shared sessions require completed onboarding for both participants.")

        session = SharedMovieNightSession(
            session_id=session_id or f"session-{uuid4().hex}",
            household_id=household_id,
            active_mode=active_mode,
            participant_ids=participant_ids,
            state=SharedSessionState.FOUNDER_REACTING,
            shortlist=shortlist,
        )
        return self.session_store.save_session(session)

    def load_session(self, session_id: str) -> SharedMovieNightSession | None:
        return self.session_store.load_session(session_id)

    def update_mode(
        self,
        session_id: str,
        active_mode: SessionMode,
    ) -> SharedMovieNightSession:
        session = self._require_session(session_id)
        if session.state == SharedSessionState.RERANKED:
            raise SessionTransitionError("Reranked sessions cannot change mode.")

        return self.session_store.save_session(
            SharedMovieNightSession(
                session_id=session.session_id,
                household_id=session.household_id,
                active_mode=active_mode,
                participant_ids=session.participant_ids,
                state=session.state,
                shortlist=session.shortlist,
                founder_reactions=session.founder_reactions,
                wife_reactions=session.wife_reactions,
                reranked_source_movie_ids=session.reranked_source_movie_ids,
            )
        )

    def submit_reactions(
        self,
        session_id: str,
        participant_id: str,
        reactions: tuple[SessionReaction, ...],
    ) -> SharedMovieNightSession:
        session = self._require_session(session_id)
        self._validate_reactions(session, participant_id, reactions)

        if session.state == SharedSessionState.FOUNDER_REACTING:
            if participant_id != session.founder_participant_id:
                raise SessionTransitionError("Founder reaction pass is active.")

            return self.session_store.save_session(
                SharedMovieNightSession(
                    session_id=session.session_id,
                    household_id=session.household_id,
                    active_mode=session.active_mode,
                    participant_ids=session.participant_ids,
                    state=SharedSessionState.HANDOFF,
                    shortlist=session.shortlist,
                    founder_reactions=reactions,
                    wife_reactions=session.wife_reactions,
                )
            )

        if session.state == SharedSessionState.WIFE_REACTING:
            if participant_id != session.wife_participant_id:
                raise SessionTransitionError("Wife reaction pass is active.")

            reranked_ids = self._rerank(session, reactions)
            return self.session_store.save_session(
                SharedMovieNightSession(
                    session_id=session.session_id,
                    household_id=session.household_id,
                    active_mode=session.active_mode,
                    participant_ids=session.participant_ids,
                    state=SharedSessionState.RERANKED,
                    shortlist=session.shortlist,
                    founder_reactions=session.founder_reactions,
                    wife_reactions=reactions,
                    reranked_source_movie_ids=reranked_ids,
                )
            )

        raise SessionTransitionError("Session is not accepting reactions right now.")

    def advance_handoff(self, session_id: str) -> SharedMovieNightSession:
        session = self._require_session(session_id)
        if session.state != SharedSessionState.HANDOFF:
            raise SessionTransitionError("Only handoff sessions can advance to wife reactions.")

        return self.session_store.save_session(
            SharedMovieNightSession(
                session_id=session.session_id,
                household_id=session.household_id,
                active_mode=session.active_mode,
                participant_ids=session.participant_ids,
                state=SharedSessionState.WIFE_REACTING,
                shortlist=session.shortlist,
                founder_reactions=session.founder_reactions,
                wife_reactions=session.wife_reactions,
            )
        )

    def _require_session(self, session_id: str) -> SharedMovieNightSession:
        session = self.session_store.load_session(session_id)
        if session is None:
            raise LookupError("Shared session not found.")
        return session

    def _validate_reactions(
        self,
        session: SharedMovieNightSession,
        participant_id: str,
        reactions: tuple[SessionReaction, ...],
    ) -> None:
        if len(reactions) != len(session.shortlist):
            raise ValueError("Each shortlist item requires exactly one reaction.")

        shortlist_ids = {item.source_movie_id for item in session.shortlist}
        reaction_ids = {reaction.source_movie_id for reaction in reactions}
        if reaction_ids != shortlist_ids:
            raise ValueError("Reaction source movie ids must match the shortlist.")

        for reaction in reactions:
            if reaction.session_id != session.session_id:
                raise ValueError("Reaction session ids must match the path session id.")

            if reaction.participant_id != participant_id:
                raise ValueError("Reaction participant ids must match the payload participant id.")

    def _rerank(
        self,
        session: SharedMovieNightSession,
        wife_reactions: tuple[SessionReaction, ...],
    ) -> tuple[str, ...]:
        founder_scores = _score_by_source_movie_id(session.founder_reactions)
        wife_scores = _score_by_source_movie_id(wife_reactions)

        def ranking_key(item: SessionShortlistItem) -> tuple[int, int]:
            combined_score = (
                founder_scores.get(item.source_movie_id, 0)
                + wife_scores.get(item.source_movie_id, 0)
            )
            return (combined_score, -item.candidate_rank)

        ranked_items = sorted(session.shortlist, key=ranking_key, reverse=True)
        return tuple(item.source_movie_id for item in ranked_items)


def _score_by_source_movie_id(
    reactions: tuple[SessionReaction, ...],
) -> dict[str, int]:
    return {
        reaction.source_movie_id: _reaction_score(reaction.reaction_label)
        for reaction in reactions
    }


def _reaction_score(reaction_label: SessionReactionLabel) -> int:
    if reaction_label == SessionReactionLabel.INTERESTED:
        return 3

    if reaction_label == SessionReactionLabel.MAYBE:
        return 2

    if reaction_label == SessionReactionLabel.NO:
        return 0

    return -100
