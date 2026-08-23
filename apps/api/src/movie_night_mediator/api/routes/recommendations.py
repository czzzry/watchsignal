from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response

from movie_night_mediator.api.recommendation_contract import (
    RecommendationProviderAvailabilityPayload,
    RecommendationShortlistItemPayload,
    RecommendationShortlistRequestPayload,
    offline_shortlist_item_to_payload,
    recommendation_request_from_payload,
)
from movie_night_mediator.app.recommendation import (
    IncompleteRecommendationError,
    RecommendationService,
    RecommendationSourceUnavailableError,
)


def register_recommendation_routes(
    app: FastAPI,
    *,
    recommendation_service: RecommendationService,
) -> None:
    @app.get(
        "/recommendations/shortlist",
        response_model=list[RecommendationShortlistItemPayload],
        tags=["recommendations"],
    )
    def get_recommendation_shortlist() -> list[RecommendationShortlistItemPayload]:
        return [
            offline_shortlist_item_to_payload(item)
            for item in recommendation_service.demo_shortlist()
        ]

    @app.post(
        "/recommendations/shortlist",
        response_model=list[RecommendationShortlistItemPayload],
        tags=["recommendations"],
    )
    def post_recommendation_shortlist(
        payload: RecommendationShortlistRequestPayload,
        response: Response = None,
    ) -> list[RecommendationShortlistItemPayload]:
        try:
            run = recommendation_service.recommend_run(
                recommendation_request_from_payload(payload)
            )
        except RecommendationSourceUnavailableError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except IncompleteRecommendationError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

        if response is not None:
            response.headers["X-WatchSignal-Run-Mode"] = run.mode.value
            response.headers["X-WatchSignal-Run-Label"] = run.label
            response.headers["X-WatchSignal-Run-Detail"] = run.detail
            response.headers["X-WatchSignal-Trained-Retrieval"] = str(
                run.trained_candidate_retrieval
            ).lower()
            response.headers["X-WatchSignal-Trained-Scoring"] = str(
                run.trained_scoring
            ).lower()
        return [offline_shortlist_item_to_payload(item) for item in run.shortlist]
