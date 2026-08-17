from __future__ import annotations

from dataclasses import dataclass
import unittest

import numpy as np

from movie_night_mediator.app.personalized_recommendation import (
    MovieLensCatalogEntry,
    PersonalizedCandidateSource,
    PersonalizedCandidateRetriever,
)
from movie_night_mediator.domain import (
    AudienceMode,
    Candidate,
    HouseholdDefaults,
    MediaType,
    ProfileTasteEvidence,
    SessionContext,
    UserProfile,
)


@dataclass(frozen=True)
class _ModelConfig:
    regularization: float = 1.0
    bias_regularization: float = 5.0


@dataclass(frozen=True)
class _Model:
    config: _ModelConfig
    global_mean: float
    item_ids: np.ndarray
    item_biases: np.ndarray
    item_factors: np.ndarray

    @property
    def item_index(self) -> dict[int, int]:
        return {int(movie_id): index for index, movie_id in enumerate(self.item_ids)}


class _Provider:
    model_name = "collaborative"

    def __init__(
        self,
        *,
        factors: np.ndarray | None = None,
        item_ids: np.ndarray | None = None,
    ) -> None:
        self.model = _Model(
            config=_ModelConfig(),
            global_mean=3.0,
            item_ids=item_ids
            if item_ids is not None
            else np.asarray([1, 2, 3, 4], dtype=np.int32),
            item_biases=np.zeros(
                len(item_ids) if item_ids is not None else 4,
                dtype=np.float32,
            ),
            item_factors=factors
            if factors is not None
            else np.asarray(
                [[0.95, 0.0], [0.05, 0.0], [0.0, 0.95], [0.0, 0.05]],
                dtype=np.float32,
            ),
        )


class _HydratingSource:
    def fetch_candidates_for_source_ids(self, *, source_movie_ids, **_kwargs):
        return tuple(
            Candidate(
                source_movie_id=source_id,
                title=f"Learned {source_id}",
                media_type=MediaType.MOVIE,
            )
            for source_id in source_movie_ids
        )

    def fetch_candidates(self, *, limit, **_kwargs):
        return tuple(
            Candidate(
                source_movie_id=f"tmdb:explore-{index}",
                title=f"Exploration {index}",
                media_type=MediaType.MOVIE,
            )
            for index in range(limit)
        )


class PersonalizedRecommendationEngineTest(unittest.TestCase):
    def test_retrieval_is_profile_driven_and_merges_content_lane(self) -> None:
        provider = _Provider()
        content_provider = _Provider(
            item_ids=np.asarray([1, 3, 4, 5], dtype=np.int32),
            factors=np.asarray(
                [[0.1, 0.0], [0.95, 0.0], [0.05, 0.0], [0.9, 0.0]],
                dtype=np.float32,
            )
        )
        catalog = (
            MovieLensCatalogEntry(1, "tmdb:101", "Profile bridge", 1995, ("Crime",)),
            MovieLensCatalogEntry(2, "tmdb:102", "Popular decoy", 2024, ("Action",)),
            MovieLensCatalogEntry(3, "tmdb:103", "Content bridge", 2001, ("Drama",)),
            MovieLensCatalogEntry(4, "tmdb:104", "Weak decoy", 2024, ("Action",)),
            MovieLensCatalogEntry(5, "tmdb:105", "Content-only bridge", 2003, ("Drama",)),
        )
        user = UserProfile(
            user_id="cezary",
            role="user_a",
            display_label="Cezary",
            taste_profile_evidence=(
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="movielens:1",
                    title="Profile seed",
                    preference_value=1.0,
                ),
            ),
        )

        retriever = PersonalizedCandidateRetriever(
            collaborative_provider=provider,
            content_provider=content_provider,
            catalog=catalog,
            minimum_profile_matches=1,
        )

        result = retriever.retrieve(users=(user,), limit=3)

        self.assertEqual(result[0].source_movie_id, "tmdb:101")
        self.assertIn("collaborative", result[0].lane)
        self.assertTrue(any("content" in row.lane for row in result))
        self.assertGreater(result[0].retrieval_score, result[-1].retrieval_score)

    def test_exclusions_and_minimum_profile_evidence_are_hard_retrieval_guards(self) -> None:
        provider = _Provider()
        catalog = (
            MovieLensCatalogEntry(1, "tmdb:101", "Profile bridge", 1995, ("Crime",)),
            MovieLensCatalogEntry(2, "tmdb:102", "Popular decoy", 2024, ("Action",)),
        )
        user = UserProfile(
            user_id="cold",
            role="user_a",
            display_label="Cold",
        )
        retriever = PersonalizedCandidateRetriever(
            collaborative_provider=provider,
            content_provider=provider,
            catalog=catalog,
            minimum_profile_matches=2,
        )

        self.assertEqual(retriever.retrieve(users=(user,), limit=5), ())
        warm_user = UserProfile(
            user_id="warm",
            role="user_a",
            display_label="Warm",
            taste_profile_evidence=(
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="movielens:1",
                    title="Profile seed",
                    preference_value=1.0,
                ),
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="movielens:2",
                    title="Second seed",
                    preference_value=0.65,
                ),
            ),
        )
        rows = retriever.retrieve(
            users=(warm_user,),
            limit=5,
            excluded_source_movie_ids=("tmdb:101",),
        )
        self.assertNotIn("tmdb:101", {row.source_movie_id for row in rows})
        self.assertTrue(rows)

    def test_source_adapter_hydrates_learned_ids_before_exploration(self) -> None:
        provider = _Provider()
        retriever = PersonalizedCandidateRetriever(
            collaborative_provider=provider,
            catalog=(
                MovieLensCatalogEntry(1, "tmdb:101", "Profile bridge"),
                MovieLensCatalogEntry(2, "tmdb:102", "Second bridge"),
            ),
            minimum_profile_matches=1,
        )
        source = PersonalizedCandidateSource(
            base_source=_HydratingSource(),
            retriever=retriever,
        )
        user = UserProfile(
            user_id="warm",
            role="user_a",
            display_label="Warm",
            taste_profile_evidence=(
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="movielens:1",
                    title="Profile seed",
                    preference_value=1.0,
                ),
            ),
        )

        candidates = source.fetch_personalized_candidates(
            session=SessionContext(
                session_id="source",
                audience_mode=AudienceMode.SOLO,
            ),
            household_defaults=HouseholdDefaults(),
            users=(user,),
            limit=2,
        )

        self.assertTrue(candidates)
        self.assertTrue(candidates[0].source_movie_id.startswith("tmdb:10"))


if __name__ == "__main__":
    unittest.main()
