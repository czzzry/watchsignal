from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from movie_night_mediator.app.outcome import SessionOutcomeService
from movie_night_mediator.app.session import SessionTransitionError, SharedSessionService
from movie_night_mediator.domain import (
    DEFAULT_HOUSEHOLD_ID,
    OutcomeSelectionOrigin,
    ScoringSessionReaction,
    SessionMode,
    SessionOutcome,
    SessionOutcomeType,
    SessionReaction,
    SessionReactionLabel,
    SessionShortlistItem,
    SharedMovieNightSession,
    SharedSessionState,
)


class SessionOutcomePayload(BaseModel):
    sessionId: str
    outcomeType: SessionOutcomeType
    selectedSourceMovieId: str | None = None
    selectedTitle: str | None = None
    selectionOrigin: OutcomeSelectionOrigin | None = None
    notes: str | None = None


class SaveSessionOutcomePayload(BaseModel):
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    outcomeType: SessionOutcomeType
    selectedSourceMovieId: str | None = None
    selectedTitle: str | None = None
    selectionOrigin: OutcomeSelectionOrigin | None = None
    notes: str | None = None


class SessionShortlistItemPayload(BaseModel):
    sourceMovieId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    candidateRank: int = Field(ge=1)
    profileScore: float = Field(default=0.0, ge=0.0, le=1.0)


class SessionReactionPayload(BaseModel):
    sourceMovieId: str = Field(min_length=1)
    reactionLabel: SessionReactionLabel


class CreateSharedSessionPayload(BaseModel):
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    activeMode: SessionMode = SessionMode.COMPROMISE
    participantIds: list[str] = Field(min_length=2, max_length=2)
    shortlist: list[SessionShortlistItemPayload] = Field(min_length=5, max_length=5)
    sessionId: str | None = None


class ContinueSharedSessionPayload(BaseModel):
    shortlist: list[SessionShortlistItemPayload] = Field(min_length=5, max_length=5)


class UpdateSharedSessionPayload(BaseModel):
    activeMode: SessionMode


class SubmitSessionReactionsPayload(BaseModel):
    participantId: str = Field(min_length=1)
    reactions: list[SessionReactionPayload] = Field(min_length=1)


class SharedSessionPayload(BaseModel):
    sessionId: str
    householdId: str
    activeMode: SessionMode
    participantIds: list[str]
    state: SharedSessionState
    shortlist: list[SessionShortlistItemPayload]
    founderReactions: list[SessionReactionPayload]
    wifeReactions: list[SessionReactionPayload]
    previousShortlist: list[SessionShortlistItemPayload]
    previousFounderReactions: list[SessionReactionPayload]
    previousWifeReactions: list[SessionReactionPayload]
    shownSourceMovieIds: list[str]
    batchCount: int
    rerankedSourceMovieIds: list[str]
    rerankedShortlist: list[SessionShortlistItemPayload]
    bestPickSourceMovieId: str | None = None


def register_session_routes(
    app: FastAPI,
    *,
    session_service: SharedSessionService,
    outcome_service: SessionOutcomeService,
) -> None:
    @app.post(
        "/sessions/{session_id}/outcome",
        response_model=SessionOutcomePayload,
        response_model_exclude_none=True,
        tags=["sessions"],
    )
    def post_session_outcome(
        session_id: str,
        payload: SaveSessionOutcomePayload,
    ) -> SessionOutcomePayload:
        try:
            outcome = outcome_service.save_outcome(
                household_id=payload.householdId,
                session_id=session_id,
                outcome_type=payload.outcomeType,
                selected_source_movie_id=payload.selectedSourceMovieId,
                selected_title=payload.selectedTitle,
                selection_origin=payload.selectionOrigin,
                notes=payload.notes,
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return session_outcome_to_payload(outcome)

    @app.post(
        "/sessions",
        response_model=SharedSessionPayload,
        tags=["sessions"],
    )
    def post_shared_session(payload: CreateSharedSessionPayload) -> SharedSessionPayload:
        try:
            session = session_service.start_session(
                household_id=payload.householdId,
                active_mode=payload.activeMode,
                participant_ids=(payload.participantIds[0], payload.participantIds[1]),
                shortlist=tuple(
                    payload_to_session_shortlist_item(item)
                    for item in payload.shortlist
                ),
                session_id=payload.sessionId,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return shared_session_to_payload(session)

    @app.get(
        "/sessions/{session_id}",
        response_model=SharedSessionPayload,
        tags=["sessions"],
    )
    def get_shared_session(session_id: str) -> SharedSessionPayload:
        session = session_service.load_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Shared session not found.")

        return shared_session_to_payload(session)

    @app.post(
        "/sessions/{session_id}/continue",
        response_model=SharedSessionPayload,
        tags=["sessions"],
    )
    def post_shared_session_continuation(
        session_id: str,
        payload: ContinueSharedSessionPayload,
    ) -> SharedSessionPayload:
        try:
            session = session_service.continue_with_shortlist(
                session_id=session_id,
                shortlist=tuple(
                    payload_to_session_shortlist_item(item)
                    for item in payload.shortlist
                ),
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SessionTransitionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return shared_session_to_payload(session)

    @app.put(
        "/sessions/{session_id}",
        response_model=SharedSessionPayload,
        tags=["sessions"],
    )
    def put_shared_session(
        session_id: str,
        payload: UpdateSharedSessionPayload,
    ) -> SharedSessionPayload:
        try:
            session = session_service.update_mode(session_id, payload.activeMode)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SessionTransitionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        return shared_session_to_payload(session)

    @app.post(
        "/sessions/{session_id}/reactions",
        response_model=SharedSessionPayload,
        tags=["sessions"],
    )
    def post_shared_session_reactions(
        session_id: str,
        payload: SubmitSessionReactionsPayload,
    ) -> SharedSessionPayload:
        try:
            session = session_service.submit_reactions(
                session_id=session_id,
                participant_id=payload.participantId,
                reactions=tuple(
                    payload_to_session_reaction(
                        session_id,
                        payload.participantId,
                        reaction,
                    )
                    for reaction in payload.reactions
                ),
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SessionTransitionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return shared_session_to_payload(session)

    @app.post(
        "/sessions/{session_id}/advance-handoff",
        response_model=SharedSessionPayload,
        tags=["sessions"],
    )
    def post_shared_session_handoff(session_id: str) -> SharedSessionPayload:
        try:
            session = session_service.advance_handoff(session_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SessionTransitionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        return shared_session_to_payload(session)


def session_outcome_to_payload(outcome: SessionOutcome) -> SessionOutcomePayload:
    return SessionOutcomePayload(
        sessionId=outcome.session_id,
        outcomeType=outcome.outcome_type,
        selectedSourceMovieId=outcome.selected_source_movie_id,
        selectedTitle=outcome.selected_title,
        selectionOrigin=outcome.selection_origin,
        notes=outcome.notes,
    )


def payload_to_session_shortlist_item(
    payload: SessionShortlistItemPayload,
) -> SessionShortlistItem:
    return SessionShortlistItem(
        source_movie_id=payload.sourceMovieId,
        title=payload.title,
        candidate_rank=payload.candidateRank,
        profile_score=payload.profileScore,
    )


def payload_to_session_reaction(
    session_id: str,
    participant_id: str,
    payload: SessionReactionPayload,
) -> SessionReaction:
    return SessionReaction(
        session_id=session_id,
        participant_id=participant_id,
        source_movie_id=payload.sourceMovieId,
        reaction_label=payload.reactionLabel,
    )


def payload_to_scoring_session_reaction(
    payload: ScoringSessionReaction,
) -> SessionReactionPayload:
    return SessionReactionPayload(
        sourceMovieId=payload.source_movie_id,
        reactionLabel=payload.reaction_label,
    )


def shared_session_to_payload(session: SharedMovieNightSession) -> SharedSessionPayload:
    shortlist_by_source_movie_id = {
        item.source_movie_id: item for item in session.shortlist
    }
    reranked_shortlist = [
        shortlist_by_source_movie_id[source_movie_id]
        for source_movie_id in session.reranked_source_movie_ids
        if source_movie_id in shortlist_by_source_movie_id
    ]

    return SharedSessionPayload(
        sessionId=session.session_id,
        householdId=session.household_id,
        activeMode=session.active_mode,
        participantIds=list(session.participant_ids),
        state=session.state,
        shortlist=[
            SessionShortlistItemPayload(
                sourceMovieId=item.source_movie_id,
                title=item.title,
                candidateRank=item.candidate_rank,
                profileScore=item.profile_score,
            )
            for item in session.shortlist
        ],
        founderReactions=[
            SessionReactionPayload(
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in session.founder_reactions
        ],
        wifeReactions=[
            SessionReactionPayload(
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in session.wife_reactions
        ],
        previousShortlist=[
            SessionShortlistItemPayload(
                sourceMovieId=item.source_movie_id,
                title=item.title,
                candidateRank=item.candidate_rank,
                profileScore=item.profile_score,
            )
            for item in session.previous_shortlist
        ],
        previousFounderReactions=[
            SessionReactionPayload(
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in session.previous_founder_reactions
        ],
        previousWifeReactions=[
            SessionReactionPayload(
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in session.previous_wife_reactions
        ],
        shownSourceMovieIds=list(session.shown_source_movie_ids),
        batchCount=session.batch_count,
        rerankedSourceMovieIds=list(session.reranked_source_movie_ids),
        rerankedShortlist=[
            SessionShortlistItemPayload(
                sourceMovieId=item.source_movie_id,
                title=item.title,
                candidateRank=item.candidate_rank,
                profileScore=item.profile_score,
            )
            for item in reranked_shortlist
        ],
        bestPickSourceMovieId=session.best_pick_source_movie_id,
    )
