from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from movie_night_mediator.app.feedback import PostWatchFeedbackService
from movie_night_mediator.domain import DEFAULT_HOUSEHOLD_ID, PostWatchFeedback


class PostWatchFeedbackPayload(BaseModel):
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    sessionId: str = Field(min_length=1)
    userId: str = Field(min_length=1)
    sourceMovieId: str = Field(min_length=1)
    feedbackLabel: str = Field(min_length=1)
    freeTextNote: str | None = None


class PostWatchFeedbackResponsePayload(BaseModel):
    sessionId: str
    userId: str
    sourceMovieId: str
    feedbackLabel: str
    freeTextNote: str | None = None


def register_feedback_routes(
    app: FastAPI,
    *,
    feedback_service: PostWatchFeedbackService,
) -> None:
    @app.post(
        "/feedback/post-watch",
        response_model=PostWatchFeedbackResponsePayload,
        response_model_exclude_none=True,
        tags=["feedback"],
    )
    def post_post_watch_feedback(
        payload: PostWatchFeedbackPayload,
    ) -> PostWatchFeedbackResponsePayload:
        try:
            feedback = feedback_service.save_feedback(
                household_id=payload.householdId,
                session_id=payload.sessionId,
                user_id=payload.userId,
                source_movie_id=payload.sourceMovieId,
                feedback_label=payload.feedbackLabel,
                free_text_note=payload.freeTextNote,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return post_watch_feedback_to_payload(feedback)

    @app.get(
        "/feedback/post-watch",
        response_model=list[PostWatchFeedbackResponsePayload],
        response_model_exclude_none=True,
        tags=["feedback"],
    )
    def get_post_watch_feedback(
        householdId: str = DEFAULT_HOUSEHOLD_ID,
        sessionId: str | None = None,
    ) -> list[PostWatchFeedbackResponsePayload]:
        try:
            feedback_records = feedback_service.list_feedback(
                household_id=householdId,
                session_id=sessionId,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return [
            post_watch_feedback_to_payload(feedback)
            for feedback in feedback_records
        ]


def post_watch_feedback_to_payload(
    feedback: PostWatchFeedback,
) -> PostWatchFeedbackResponsePayload:
    return PostWatchFeedbackResponsePayload(
        sessionId=feedback.session_id,
        userId=feedback.user_id,
        sourceMovieId=feedback.source_movie_id,
        feedbackLabel=feedback.feedback_label,
        freeTextNote=feedback.free_text_note,
    )
