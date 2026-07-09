from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from movie_night_mediator.taste_lab import (
    TasteLabCandidate,
    TasteLabMovieIdentity,
    TasteLabQueueProvenance,
    TasteLabRatingExport,
    TasteLabRatingInput,
    TasteLabRatingLabel,
    TasteLabService,
    TasteGenreSignal,
    TasteProfileEvidence,
    TasteProfileSummary,
    default_taste_lab_candidates,
)
from movie_night_mediator.domain import DEFAULT_HOUSEHOLD_ID


class TasteLabMoviePayload(BaseModel):
    sourceMovieId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    releaseYear: int | None = None
    tmdbId: str | None = None
    posterPath: str | None = None
    genres: list[str] = Field(default_factory=list)


class TasteLabQueueProvenancePayload(BaseModel):
    queueSource: str = Field(min_length=1)
    generatedAt: str | None = None
    rank: int | None = None
    signalScore: float | None = None
    scoreComponents: dict[str, float] = Field(default_factory=dict)
    queueReason: str | None = None


class TasteLabCandidatePayload(BaseModel):
    movie: TasteLabMoviePayload
    queueProvenance: TasteLabQueueProvenancePayload


class TasteLabRatingInputPayload(BaseModel):
    movie: TasteLabMoviePayload
    label: TasteLabRatingLabel
    queueProvenance: TasteLabQueueProvenancePayload | None = None
    ratedAt: str | None = None


class TasteLabSubmitRatingsPayload(BaseModel):
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    ratings: list[TasteLabRatingInputPayload] = Field(min_length=1)


class TasteLabRatingExportPayload(BaseModel):
    schemaVersion: str
    householdId: str
    profileId: str
    movie: TasteLabMoviePayload
    label: TasteLabRatingLabel
    familiarity: str
    preferenceValue: float | None = None
    watchsignalTasteSignal: str
    isImportablePreference: bool
    ratedAt: str
    queueProvenance: TasteLabQueueProvenancePayload | None = None


class TasteGenreSignalPayload(BaseModel):
    genre: str
    positiveCount: int
    neutralCount: int
    negativeCount: int
    score: float


class TasteProfileEvidencePayload(BaseModel):
    source: str
    householdId: str
    profileId: str
    sourceMovieId: str
    title: str
    releaseYear: int | None = None
    tmdbId: str | None = None
    genres: list[str]
    label: str
    familiarity: str
    watchsignalTasteSignal: str
    isPreferenceEvidence: bool
    preferenceValue: float | None = None
    ratedAt: str
    queueProvenance: TasteLabQueueProvenancePayload | None = None


class TasteProfileSummaryPayload(BaseModel):
    householdId: str
    profileId: str
    ratingCount: int
    preferenceEvidenceCount: int
    familiarityOnlyCount: int
    genreSignals: list[TasteGenreSignalPayload]
    evidence: list[TasteProfileEvidencePayload]


def register_taste_lab_routes(
    app: FastAPI,
    *,
    taste_lab_service: TasteLabService,
    taste_lab_seed_queue_path: Path | str | None,
) -> None:
    @app.post(
        "/taste-lab/candidates",
        status_code=204,
        tags=["taste-lab"],
    )
    def post_taste_lab_candidates(
        candidates: list[TasteLabCandidatePayload],
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> None:
        try:
            taste_lab_service.seed_candidates(
                household_id=householdId,
                candidates=tuple(
                    payload_to_taste_lab_candidate(candidate)
                    for candidate in candidates
                ),
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post(
        "/taste-lab/default-candidates",
        status_code=204,
        tags=["taste-lab"],
    )
    def post_default_taste_lab_candidates(
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> None:
        try:
            taste_lab_service.seed_candidates(
                household_id=householdId,
                candidates=default_taste_lab_candidates(taste_lab_seed_queue_path),
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.get(
        "/taste-lab/{profile_id}/queue",
        response_model=list[TasteLabCandidatePayload],
        tags=["taste-lab"],
    )
    def get_taste_lab_queue(
        profile_id: str,
        householdId: str = DEFAULT_HOUSEHOLD_ID,
        limit: int = Query(default=10, ge=1, le=25),
    ) -> list[TasteLabCandidatePayload]:
        try:
            candidates = taste_lab_service.next_batch(
                household_id=householdId,
                profile_id=profile_id,
                limit=limit,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return [taste_lab_candidate_to_payload(candidate) for candidate in candidates]

    @app.post(
        "/taste-lab/{profile_id}/ratings",
        response_model=list[TasteLabRatingExportPayload],
        tags=["taste-lab"],
    )
    def post_taste_lab_ratings(
        profile_id: str,
        payload: TasteLabSubmitRatingsPayload,
    ) -> list[TasteLabRatingExportPayload]:
        try:
            ratings = taste_lab_service.submit_batch(
                household_id=payload.householdId,
                profile_id=profile_id,
                ratings=tuple(
                    payload_to_taste_lab_rating_input(rating)
                    for rating in payload.ratings
                ),
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return [taste_lab_rating_export_to_payload(rating) for rating in ratings]

    @app.get(
        "/taste-lab/{profile_id}/ratings",
        response_model=list[TasteLabRatingExportPayload],
        tags=["taste-lab"],
    )
    def get_taste_lab_ratings(
        profile_id: str,
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> list[TasteLabRatingExportPayload]:
        try:
            ratings = taste_lab_service.list_profile_ratings(
                household_id=householdId,
                profile_id=profile_id,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return [taste_lab_rating_export_to_payload(rating) for rating in ratings]

    @app.get(
        "/taste-profile/{profile_id}/summary",
        response_model=TasteProfileSummaryPayload,
        tags=["taste-profile"],
    )
    def get_taste_profile_summary(
        profile_id: str,
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> TasteProfileSummaryPayload:
        try:
            summary = taste_lab_service.taste_profile_summary(
                household_id=householdId,
                profile_id=profile_id,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return taste_profile_summary_to_payload(summary)


def payload_to_taste_lab_candidate(payload: TasteLabCandidatePayload) -> TasteLabCandidate:
    return TasteLabCandidate(
        movie=payload_to_taste_lab_movie(payload.movie),
        queue_provenance=payload_to_taste_lab_queue_provenance(
            payload.queueProvenance
        ),
    )


def payload_to_taste_lab_rating_input(
    payload: TasteLabRatingInputPayload,
) -> TasteLabRatingInput:
    return TasteLabRatingInput(
        movie=payload_to_taste_lab_movie(payload.movie),
        label=payload.label,
        rated_at=payload.ratedAt,
        queue_provenance=(
            payload_to_taste_lab_queue_provenance(payload.queueProvenance)
            if payload.queueProvenance is not None
            else None
        ),
    )


def payload_to_taste_lab_movie(payload: TasteLabMoviePayload) -> TasteLabMovieIdentity:
    return TasteLabMovieIdentity(
        source_movie_id=payload.sourceMovieId,
        title=payload.title,
        release_year=payload.releaseYear,
        tmdb_id=payload.tmdbId,
        poster_path=payload.posterPath,
        genres=tuple(payload.genres),
    )


def payload_to_taste_lab_queue_provenance(
    payload: TasteLabQueueProvenancePayload,
) -> TasteLabQueueProvenance:
    return TasteLabQueueProvenance(
        queue_source=payload.queueSource,
        generated_at=payload.generatedAt,
        rank=payload.rank,
        signal_score=payload.signalScore,
        score_components=payload.scoreComponents,
        queue_reason=payload.queueReason,
    )


def taste_lab_candidate_to_payload(
    candidate: TasteLabCandidate,
) -> TasteLabCandidatePayload:
    return TasteLabCandidatePayload(
        movie=taste_lab_movie_to_payload(candidate.movie),
        queueProvenance=taste_lab_queue_provenance_to_payload(
            candidate.queue_provenance
        ),
    )


def taste_lab_rating_export_to_payload(
    rating: TasteLabRatingExport,
) -> TasteLabRatingExportPayload:
    return TasteLabRatingExportPayload(
        schemaVersion=rating.schema_version,
        householdId=rating.household_id,
        profileId=rating.profile_id,
        movie=taste_lab_movie_to_payload(rating.movie),
        label=rating.label,
        familiarity=rating.familiarity.value,
        preferenceValue=rating.preference_value,
        watchsignalTasteSignal=rating.watchsignal_taste_signal.value,
        isImportablePreference=rating.is_importable_preference,
        ratedAt=rating.rated_at,
        queueProvenance=(
            taste_lab_queue_provenance_to_payload(rating.queue_provenance)
            if rating.queue_provenance is not None
            else None
        ),
    )


def taste_profile_summary_to_payload(
    summary: TasteProfileSummary,
) -> TasteProfileSummaryPayload:
    return TasteProfileSummaryPayload(
        householdId=summary.household_id,
        profileId=summary.profile_id,
        ratingCount=summary.rating_count,
        preferenceEvidenceCount=summary.preference_evidence_count,
        familiarityOnlyCount=summary.familiarity_only_count,
        genreSignals=[
            taste_genre_signal_to_payload(signal) for signal in summary.genre_signals
        ],
        evidence=[
            taste_profile_evidence_to_payload(evidence)
            for evidence in summary.evidence
        ],
    )


def taste_profile_evidence_to_payload(
    evidence: TasteProfileEvidence,
) -> TasteProfileEvidencePayload:
    return TasteProfileEvidencePayload(
        source=evidence.source,
        householdId=evidence.household_id,
        profileId=evidence.profile_id,
        sourceMovieId=evidence.source_movie_id,
        title=evidence.title,
        releaseYear=evidence.release_year,
        tmdbId=evidence.tmdb_id,
        genres=list(evidence.genres),
        label=evidence.label,
        familiarity=evidence.familiarity.value,
        watchsignalTasteSignal=evidence.watchsignal_taste_signal.value,
        isPreferenceEvidence=evidence.is_preference_evidence,
        preferenceValue=evidence.preference_value,
        ratedAt=evidence.rated_at,
        queueProvenance=(
            taste_lab_queue_provenance_to_payload(evidence.queue_provenance)
            if evidence.queue_provenance is not None
            else None
        ),
    )


def taste_genre_signal_to_payload(signal: TasteGenreSignal) -> TasteGenreSignalPayload:
    return TasteGenreSignalPayload(
        genre=signal.genre,
        positiveCount=signal.positive_count,
        neutralCount=signal.neutral_count,
        negativeCount=signal.negative_count,
        score=signal.score,
    )


def taste_lab_movie_to_payload(movie: TasteLabMovieIdentity) -> TasteLabMoviePayload:
    return TasteLabMoviePayload(
        sourceMovieId=movie.source_movie_id,
        title=movie.title,
        releaseYear=movie.release_year,
        tmdbId=movie.tmdb_id,
        posterPath=movie.poster_path,
        genres=list(movie.genres),
    )


def taste_lab_queue_provenance_to_payload(
    provenance: TasteLabQueueProvenance,
) -> TasteLabQueueProvenancePayload:
    return TasteLabQueueProvenancePayload(
        queueSource=provenance.queue_source,
        generatedAt=provenance.generated_at,
        rank=provenance.rank,
        signalScore=provenance.signal_score,
        scoreComponents=dict(provenance.score_components),
        queueReason=provenance.queue_reason,
    )
