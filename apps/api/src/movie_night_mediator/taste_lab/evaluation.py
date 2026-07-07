from __future__ import annotations

from dataclasses import dataclass

from movie_night_mediator.domain import (
    AudienceMode,
    Candidate,
    HouseholdDefaults,
    MediaType,
    OnboardingSeed,
    ScoringRequest,
    SessionContext,
    SessionMode,
    UserProfile,
)
from movie_night_mediator.scoring import HeuristicScorer
from movie_night_mediator.taste_lab.export_contract import (
    TasteLabMovieIdentity,
    TasteLabQueueProvenance,
    TasteLabRatingExport,
    TasteLabRatingLabel,
)
from movie_night_mediator.taste_lab.profile import build_taste_profile_summary
from movie_night_mediator.taste_lab.service import TasteLabCandidate, TasteLabService

TARGET_SOURCE_MOVIE_ID = "fixture:shared-puzzle"


@dataclass(frozen=True)
class TasteLabEvaluationStrategy:
    name: str
    description: str
    sandy_ratings: tuple[TasteLabRatingExport, ...] = ()
    robin_ratings: tuple[TasteLabRatingExport, ...] = ()


@dataclass(frozen=True)
class TasteLabEvaluationRow:
    source_movie_id: str
    title: str
    rank: int
    group_score: float
    sandy_score: float | None
    robin_score: float | None
    why_short: str

    def as_dict(self) -> dict[str, object]:
        return {
            "source_movie_id": self.source_movie_id,
            "title": self.title,
            "rank": self.rank,
            "group_score": self.group_score,
            "sandy_score": self.sandy_score,
            "robin_score": self.robin_score,
            "why_short": self.why_short,
        }


@dataclass(frozen=True)
class TasteLabEvaluationResult:
    strategy_name: str
    description: str
    target_source_movie_id: str
    target_rank: int | None
    target_why_short: str | None
    top_pick_source_movie_id: str | None
    top_pick_title: str | None
    ranked_rows: tuple[TasteLabEvaluationRow, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy_name": self.strategy_name,
            "description": self.description,
            "target_source_movie_id": self.target_source_movie_id,
            "target_rank": self.target_rank,
            "target_why_short": self.target_why_short,
            "top_pick_source_movie_id": self.top_pick_source_movie_id,
            "top_pick_title": self.top_pick_title,
            "taste_lab_influenced_rows": sum(
                1 for row in self.ranked_rows if "Taste Lab" in row.why_short
            ),
            "ranked_rows": [row.as_dict() for row in self.ranked_rows],
        }


@dataclass(frozen=True)
class TasteLabEvaluationReport:
    target_title: str
    baseline_strategy_name: str
    results: tuple[TasteLabEvaluationResult, ...]

    def as_dict(self) -> dict[str, object]:
        baseline = next(
            result
            for result in self.results
            if result.strategy_name == self.baseline_strategy_name
        )
        return {
            "target_title": self.target_title,
            "baseline_strategy_name": self.baseline_strategy_name,
            "results": [result.as_dict() for result in self.results],
            "rank_deltas_vs_baseline": {
                result.strategy_name: _rank_delta(baseline.target_rank, result.target_rank)
                for result in self.results
            },
            "top_pick_changes_vs_baseline": {
                result.strategy_name: result.top_pick_source_movie_id != baseline.top_pick_source_movie_id
                for result in self.results
            },
            "interpretation": (
                "Positive rank deltas mean the target shared-fit movie moved closer "
                "to rank 1 compared with the no-taste baseline."
            ),
        }


@dataclass(frozen=True)
class TasteLabCalibrationQueueCoverageReport:
    naive_genre_coverage: tuple[str, ...]
    informative_genre_coverage: tuple[str, ...]
    naive_partner_prompt_count: int
    informative_partner_prompt_count: int
    informative_reasons: tuple[str, ...]

    @property
    def improves_coverage(self) -> bool:
        return (
            len(self.informative_genre_coverage) > len(self.naive_genre_coverage)
            and self.informative_partner_prompt_count
            > self.naive_partner_prompt_count
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "naive_genre_coverage": list(self.naive_genre_coverage),
            "informative_genre_coverage": list(self.informative_genre_coverage),
            "naive_partner_prompt_count": self.naive_partner_prompt_count,
            "informative_partner_prompt_count": self.informative_partner_prompt_count,
            "informative_reasons": list(self.informative_reasons),
            "improves_coverage": self.improves_coverage,
        }


def run_fixture_evaluation() -> TasteLabEvaluationReport:
    strategies = (
        TasteLabEvaluationStrategy(
            name="no_taste_lab",
            description="No Taste Lab ratings. This is the cold-start baseline.",
        ),
        TasteLabEvaluationStrategy(
            name="popularity_seeded",
            description=(
                "Popular but weakly targeted ratings. This simulates basic seed data "
                "that may not clarify shared taste boundaries."
            ),
            sandy_ratings=(
                _rating("sandy", "Arrival", ("Sci-Fi", "Drama"), TasteLabRatingLabel.LOVED),
            ),
            robin_ratings=(
                _rating("robin", "Before Sunrise", ("Romance", "Drama"), TasteLabRatingLabel.LOVED),
            ),
        ),
        TasteLabEvaluationStrategy(
            name="high_signal_seeded",
            description=(
                "High-signal ratings with positive shared-comedy/mystery evidence "
                "and negative one-sided boundary evidence."
            ),
            sandy_ratings=(
                _rating("sandy", "Knives Out", ("Mystery", "Comedy"), TasteLabRatingLabel.LOVED),
                _rating("sandy", "The Raid", ("Action", "Thriller"), TasteLabRatingLabel.HATED),
            ),
            robin_ratings=(
                _rating("robin", "Paddington", ("Comedy",), TasteLabRatingLabel.LOVED),
                _rating("robin", "Knives Out", ("Mystery", "Comedy"), TasteLabRatingLabel.LIKED),
                _rating("robin", "Saw", ("Horror",), TasteLabRatingLabel.HATED),
            ),
        ),
    )

    return TasteLabEvaluationReport(
        target_title="Shared Puzzle",
        baseline_strategy_name="no_taste_lab",
        results=tuple(evaluate_strategy(strategy) for strategy in strategies),
    )


def evaluate_calibration_queue_coverage() -> TasteLabCalibrationQueueCoverageReport:
    candidates = (
        _lab_candidate("fixture:drama-one", "Drama One", ("Drama",), rank=1),
        _lab_candidate("fixture:drama-two", "Drama Two", ("Drama",), rank=2),
        _lab_candidate("fixture:drama-three", "Drama Three", ("Drama",), rank=3),
        _lab_candidate("fixture:shared-comedy", "Shared Comedy", ("Comedy",), rank=8),
        _lab_candidate("fixture:horror-boundary", "Horror Boundary", ("Horror",), rank=9),
    )
    sandy_ratings = (
        _rating("sandy", "Drama Seed", ("Drama",), TasteLabRatingLabel.LOVED),
    )
    robin_ratings = (
        _rating("robin", "Shared Comedy", ("Comedy",), TasteLabRatingLabel.LOVED),
        _rating("robin", "Horror Boundary", ("Horror",), TasteLabRatingLabel.HATED),
    )
    store = _FixtureTasteLabStore(
        candidates=candidates,
        ratings=(*sandy_ratings, *robin_ratings),
    )
    informative_queue = TasteLabService(store).next_batch(
        household_id="default-household",
        profile_id="sandy",
        limit=3,
    )
    naive_queue = candidates[:3]

    return TasteLabCalibrationQueueCoverageReport(
        naive_genre_coverage=_queue_genre_coverage(naive_queue),
        informative_genre_coverage=_queue_genre_coverage(informative_queue),
        naive_partner_prompt_count=_partner_prompt_count(naive_queue),
        informative_partner_prompt_count=_partner_prompt_count(informative_queue),
        informative_reasons=tuple(
            candidate.queue_provenance.queue_reason or ""
            for candidate in informative_queue
        ),
    )


def evaluate_strategy(
    strategy: TasteLabEvaluationStrategy,
) -> TasteLabEvaluationResult:
    result = HeuristicScorer().score(
        ScoringRequest(
            session=SessionContext(
                session_id=f"taste-lab-eval-{strategy.name}",
                audience_mode=AudienceMode.SHARED,
                session_mode=SessionMode.COMPROMISE,
                viewer_user_ids=("sandy", "robin"),
            ),
            household_defaults=HouseholdDefaults(),
            users=(
                _profile("sandy", "Sandy", strategy.sandy_ratings),
                _profile("robin", "Robin", strategy.robin_ratings),
            ),
            candidates=_evaluation_candidates(),
        )
    )
    rows = tuple(
        TasteLabEvaluationRow(
            source_movie_id=candidate.source_movie_id,
            title=candidate.title,
            rank=candidate.candidate_rank,
            group_score=candidate.group_score,
            sandy_score=candidate.user_a_score,
            robin_score=candidate.user_b_score,
            why_short=candidate.why_short,
        )
        for candidate in result.ranked_candidates
    )
    target_row = next(
        (row for row in rows if row.source_movie_id == TARGET_SOURCE_MOVIE_ID),
        None,
    )
    top_row = rows[0] if rows else None
    return TasteLabEvaluationResult(
        strategy_name=strategy.name,
        description=strategy.description,
        target_source_movie_id=TARGET_SOURCE_MOVIE_ID,
        target_rank=target_row.rank if target_row else None,
        target_why_short=target_row.why_short if target_row else None,
        top_pick_source_movie_id=top_row.source_movie_id if top_row else None,
        top_pick_title=top_row.title if top_row else None,
        ranked_rows=rows,
    )


def taste_lab_ratings_to_onboarding_seeds(
    ratings: tuple[TasteLabRatingExport, ...],
) -> tuple[OnboardingSeed, ...]:
    seeds: list[OnboardingSeed] = []
    for rating in ratings:
        if not rating.is_importable_preference:
            continue
        scorer_label = _scorer_label(rating.label)
        if scorer_label is None:
            continue
        seeds.append(
            OnboardingSeed(
                title=rating.movie.title,
                label=scorer_label,
                genres=rating.movie.genres,
                notes=f"Taste Lab import: {rating.label.value}",
            )
        )
    return tuple(seeds)


class _FixtureTasteLabStore:
    def __init__(
        self,
        *,
        candidates: tuple[TasteLabCandidate, ...],
        ratings: tuple[TasteLabRatingExport, ...],
    ) -> None:
        self.candidates = candidates
        self.ratings = ratings

    def upsert_candidates(
        self,
        *,
        household_id: str,
        candidates: tuple[TasteLabCandidate, ...],
    ) -> None:
        self.candidates = candidates

    def list_candidates(self, *, household_id: str) -> tuple[TasteLabCandidate, ...]:
        return self.candidates

    def save_ratings(
        self,
        *,
        ratings: tuple[TasteLabRatingExport, ...],
    ) -> tuple[TasteLabRatingExport, ...]:
        self.ratings = (*self.ratings, *ratings)
        return ratings

    def list_ratings(
        self,
        *,
        household_id: str,
        profile_id: str,
    ) -> tuple[TasteLabRatingExport, ...]:
        return tuple(
            rating
            for rating in self.ratings
            if rating.household_id == household_id and rating.profile_id == profile_id
        )

    def list_household_ratings(
        self,
        *,
        household_id: str,
    ) -> tuple[TasteLabRatingExport, ...]:
        return tuple(
            rating
            for rating in self.ratings
            if rating.household_id == household_id
        )


def _lab_candidate(
    source_movie_id: str,
    title: str,
    genres: tuple[str, ...],
    *,
    rank: int,
) -> TasteLabCandidate:
    return TasteLabCandidate(
        movie=TasteLabMovieIdentity(
            source_movie_id=source_movie_id,
            title=title,
            genres=genres,
        ),
        queue_provenance=TasteLabQueueProvenance(
            queue_source="fixture_signal_queue",
            rank=rank,
            signal_score=1 - (rank / 20),
            score_components={
                "divisiveness": 0.9,
                "discrimination_proxy": 0.9,
                "coverage": 0.9,
                "non_redundancy": 0.9,
            },
        ),
    )


def _queue_genre_coverage(
    queue: tuple[TasteLabCandidate, ...],
) -> tuple[str, ...]:
    return tuple(
        sorted({
            genre
            for candidate in queue
            for genre in candidate.movie.genres
        })
    )


def _partner_prompt_count(queue: tuple[TasteLabCandidate, ...]) -> int:
    return sum(
        1
        for candidate in queue
        if candidate.queue_provenance.queue_reason
        in {"partner_compromise_probe", "partner_disagreement_probe"}
    )


def _evaluation_candidates() -> tuple[Candidate, ...]:
    return (
        _candidate("fixture:laser-chase", "Laser Chase", ("Action", "Sci-Fi")),
        _candidate("fixture:quiet-goodbye", "Quiet Goodbye", ("Romance", "Drama")),
        _candidate(TARGET_SOURCE_MOVIE_ID, "Shared Puzzle", ("Mystery", "Comedy")),
        _candidate("fixture:horror-night", "Horror Night", ("Horror", "Thriller")),
        _candidate("fixture:slow-planet", "Slow Planet", ("Sci-Fi", "Drama")),
    )


def _candidate(
    source_movie_id: str,
    title: str,
    genres: tuple[str, ...],
) -> Candidate:
    return Candidate(
        source_movie_id=source_movie_id,
        title=title,
        media_type=MediaType.MOVIE,
        genres=genres,
        providers=("Prime Video",),
    )


def _profile(
    profile_id: str,
    display_label: str,
    ratings: tuple[TasteLabRatingExport, ...],
) -> UserProfile:
    summary = build_taste_profile_summary(
        household_id="default-household",
        profile_id=profile_id,
        ratings=ratings,
    )
    return UserProfile(
        user_id=profile_id,
        role=profile_id,
        display_label=display_label,
        taste_profile_evidence=summary.watchsignal_taste_evidence,
    )


def _rating(
    profile_id: str,
    title: str,
    genres: tuple[str, ...],
    label: TasteLabRatingLabel,
) -> TasteLabRatingExport:
    return TasteLabRatingExport(
        profile_id=profile_id,
        movie=TasteLabMovieIdentity(
            source_movie_id=f"fixture:{title.lower().replace(' ', '-')}",
            title=title,
            genres=genres,
        ),
        label=label,
        rated_at="2026-07-01T12:00:00Z",
    )


def _scorer_label(label: TasteLabRatingLabel) -> str | None:
    if label == TasteLabRatingLabel.LOVED:
        return "loved"
    if label in {TasteLabRatingLabel.LIKED, TasteLabRatingLabel.MEH}:
        return "fine"
    if label == TasteLabRatingLabel.HATED:
        return "no"
    return None


def _rank_delta(baseline_rank: int | None, strategy_rank: int | None) -> int | None:
    if baseline_rank is None or strategy_rank is None:
        return None
    return baseline_rank - strategy_rank
