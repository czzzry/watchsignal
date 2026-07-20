from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from movie_night_mediator.app.tonight_intent import TonightIntentInterpreter
from movie_night_mediator.mvp_plus_2 import (
    IntentInterpretation,
    IntentInterpretationStatus,
)
from movie_night_mediator.mvp_plus_3 import DirectedNudge


class TonightIntentInterpretRequestPayload(BaseModel):
    text: str = Field(min_length=1)


class TonightIntentInterpretationPayload(BaseModel):
    rawText: str
    status: IntentInterpretationStatus
    resolution: Literal["exact", "guess", "unsupported"] = "exact"
    confirmationText: str | None = None
    clarificationQuestion: str | None = None
    unsupportedReason: str | None = None
    filters: dict[str, object]
    softSignals: list[str]
    excludedSignals: list[str] = Field(default_factory=list)
    confidence: str


def register_tonight_intent_routes(
    app: FastAPI,
    *,
    tonight_intent_interpreter: TonightIntentInterpreter,
) -> None:
    @app.post(
        "/tonight-intent/interpret",
        response_model=TonightIntentInterpretationPayload,
        response_model_exclude_none=True,
        tags=["tonight-intent"],
    )
    def post_tonight_intent_interpretation(
        payload: TonightIntentInterpretRequestPayload,
    ) -> TonightIntentInterpretationPayload:
        try:
            interpretation = tonight_intent_interpreter.interpret(payload.text)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return intent_interpretation_to_payload(interpretation)

    @app.post(
        "/tonight-intent/direct-nudge",
        response_model=TonightIntentInterpretationPayload,
        response_model_exclude_none=True,
        tags=["tonight-intent"],
    )
    def post_directed_nudge_interpretation(
        payload: TonightIntentInterpretRequestPayload,
    ) -> TonightIntentInterpretationPayload:
        try:
            nudge = tonight_intent_interpreter.interpret_directed_nudge(payload.text)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return directed_nudge_to_payload(nudge)


def intent_interpretation_to_payload(
    interpretation: IntentInterpretation,
) -> TonightIntentInterpretationPayload:
    return TonightIntentInterpretationPayload(
        rawText=interpretation.raw_text,
        status=interpretation.status,
        resolution="exact",
        confirmationText=interpretation.confirmation_text,
        clarificationQuestion=interpretation.clarification_question,
        unsupportedReason=None,
        filters=dict(interpretation.filters),
        softSignals=list(interpretation.soft_signals),
        excludedSignals=[],
        confidence=interpretation.confidence,
    )


def directed_nudge_to_payload(
    nudge: DirectedNudge,
) -> TonightIntentInterpretationPayload:
    return TonightIntentInterpretationPayload(
        rawText=nudge.raw_text,
        status=nudge.status,
        resolution=nudge.resolution,
        confirmationText=nudge.user_facing_summary,
        clarificationQuestion=nudge.clarification_question,
        unsupportedReason=nudge.unsupported_reason,
        filters=dict(nudge.filters),
        softSignals=list(nudge.soft_signals),
        excludedSignals=list(nudge.excluded_signals),
        confidence=nudge.confidence,
    )
