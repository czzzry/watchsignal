from __future__ import annotations

from fastapi import FastAPI, HTTPException

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
    ) -> list[RecommendationShortlistItemPayload]:
        try:
            shortlist = recommendation_service.recommend(
                recommendation_request_from_payload(payload)
            )
        except RecommendationSourceUnavailableError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except IncompleteRecommendationError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

        return [offline_shortlist_item_to_payload(item) for item in shortlist]
