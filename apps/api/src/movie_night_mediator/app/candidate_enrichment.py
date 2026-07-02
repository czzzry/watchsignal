from __future__ import annotations

from dataclasses import dataclass, replace

from movie_night_mediator.domain import Candidate
from movie_night_mediator.mvp_plus_2 import (
    CandidateEnrichment,
    CandidateEnrichmentStatus,
    EvaluationCoverage,
)

ENRICHMENT_PROVIDER = "movielens-tag-genome-fixture"
FALLBACK_PROVIDER = "tmdb-metadata-fallback"


@dataclass(frozen=True)
class OfflineFeatureRecord:
    matched_source_movie_id: str
    title: str
    release_year: int | None
    feature_scores: dict[str, float]


OFFLINE_FEATURE_FIXTURES: tuple[OfflineFeatureRecord, ...] = (
    OfflineFeatureRecord(
        matched_source_movie_id="movielens:122882",
        title="Arrival",
        release_year=2016,
        feature_scores={
            "cerebral": 0.91,
            "emotional": 0.78,
            "first-contact": 0.94,
            "slow-burn": 0.66,
        },
    ),
    OfflineFeatureRecord(
        matched_source_movie_id="movielens:188301",
        title="Knives Out",
        release_year=2019,
        feature_scores={
            "whodunit": 0.96,
            "witty": 0.88,
            "ensemble": 0.78,
            "low-homework": 0.73,
        },
    ),
    OfflineFeatureRecord(
        matched_source_movie_id="movielens:115569",
        title="The Grand Budapest Hotel",
        release_year=2014,
        feature_scores={
            "stylized": 0.95,
            "quirky": 0.84,
            "brisk": 0.71,
            "charming": 0.76,
        },
    ),
    OfflineFeatureRecord(
        matched_source_movie_id="movielens:111759",
        title="Edge of Tomorrow",
        release_year=2014,
        feature_scores={
            "time-loop": 0.94,
            "action": 0.87,
            "playful": 0.72,
            "high-energy": 0.85,
        },
    ),
    OfflineFeatureRecord(
        matched_source_movie_id="movielens:205383",
        title="Past Lives",
        release_year=2023,
        feature_scores={
            "reflective": 0.92,
            "romantic": 0.81,
            "quiet": 0.79,
            "bittersweet": 0.88,
        },
    ),
)


class CandidateEnrichmentService:
    def __init__(
        self,
        records: tuple[OfflineFeatureRecord, ...] = OFFLINE_FEATURE_FIXTURES,
    ) -> None:
        self._records_by_source_movie_id = {
            record.matched_source_movie_id: record for record in records
        }
        self._records_by_title_year = {
            (_normalize(record.title), record.release_year): record for record in records
        }
        self._records_by_title = {_normalize(record.title): record for record in records}

    def enrich_candidates(self, candidates: tuple[Candidate, ...]) -> tuple[Candidate, ...]:
        return tuple(self.enrich_candidate(candidate) for candidate in candidates)

    def enrich_candidate(self, candidate: Candidate) -> Candidate:
        enrichment = self.enrichment_for_candidate(candidate)
        return replace(
            candidate,
            enrichment_status=enrichment.status.value,
            enrichment_provider=enrichment.provider,
            enrichment_feature_scores=dict(enrichment.feature_scores),
            matched_enrichment_source_movie_id=enrichment.matched_source_movie_id,
        )

    def enrichment_for_candidate(self, candidate: Candidate) -> CandidateEnrichment:
        record = self._match_record(candidate)
        if record is None:
            return CandidateEnrichment(
                source_movie_id=candidate.source_movie_id,
                status=CandidateEnrichmentStatus.FALLBACK,
                provider=FALLBACK_PROVIDER,
            )

        return CandidateEnrichment(
            source_movie_id=candidate.source_movie_id,
            status=CandidateEnrichmentStatus.ENRICHED,
            provider=ENRICHMENT_PROVIDER,
            matched_source_movie_id=record.matched_source_movie_id,
            feature_scores=record.feature_scores,
        )

    def coverage_for_candidates(
        self,
        candidates: tuple[Candidate, ...],
        *,
        scenario_name: str,
    ) -> EvaluationCoverage:
        enriched_count = sum(
            1 for candidate in candidates if candidate.enrichment_status == "enriched"
        )
        candidate_count = len(candidates)
        return EvaluationCoverage(
            scenario_name=scenario_name,
            candidate_count=candidate_count,
            enriched_candidate_count=enriched_count,
            fallback_candidate_count=candidate_count - enriched_count,
        )

    def _match_record(self, candidate: Candidate) -> OfflineFeatureRecord | None:
        exact_match = self._records_by_source_movie_id.get(candidate.source_movie_id)
        if exact_match is not None:
            return exact_match

        normalized_title = _normalize(candidate.title)
        title_year_match = self._records_by_title_year.get(
            (normalized_title, candidate.release_year)
        )
        if title_year_match is not None:
            return title_year_match

        return self._records_by_title.get(normalized_title)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())
