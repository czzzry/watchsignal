from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import csv
import hashlib
import heapq
import io
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable
from zipfile import ZipFile


SOURCE_URL = "https://files.grouplens.org/datasets/movielens/ml-32m.zip"
DATASET_GENERATED_DATE = "2023-10-13"
REPORT_DATE = "2026-07-10"
PILOT_SEED = 20260710
POSITIVE_THRESHOLD = 4.0
NEGATIVE_THRESHOLD = 2.5
SAMPLE_EFFECTS = (0.01, 0.02, 0.03)
Z_95_TWO_SIDED = 1.96
Z_80_POWER = 0.841621


@dataclass(frozen=True)
class CohortSpec:
    name: str
    history_size: int
    holdout_size: int
    purpose: str
    window_anchor: str = "end"

    def __post_init__(self) -> None:
        if self.window_anchor not in {"start", "end"}:
            raise ValueError("Cohort window anchor must be start or end.")

    @property
    def minimum_ratings(self) -> int:
        return self.history_size + self.holdout_size


DEFAULT_COHORTS = (
    CohortSpec(
        name="cold_start",
        history_size=10,
        holdout_size=10,
        purpose="Diagnostic for profiles that resemble early product use.",
        window_anchor="start",
    ),
    CohortSpec(
        name="sparse_recent_profile",
        history_size=10,
        holdout_size=10,
        purpose=(
            "Diagnostic for a small visible profile immediately before a later outcome "
            "window; this is not true first-use cold start."
        ),
    ),
    CohortSpec(
        name="established",
        history_size=100,
        holdout_size=30,
        purpose="Primary candidate for stable solo-taste evaluation.",
    ),
    CohortSpec(
        name="deep_history",
        history_size=500,
        holdout_size=50,
        purpose="Deep evidence cohort for richer feature and learning experiments.",
    ),
    CohortSpec(
        name="prolific",
        history_size=1000,
        holdout_size=100,
        purpose="Sensitivity cohort for unusually prolific MovieLens users.",
    ),
)


@dataclass(frozen=True)
class RatingRecord:
    movie_id: int
    rating: float
    timestamp: int


@dataclass
class CohortAccumulator:
    spec: CohortSpec
    eligible_users: int = 0
    profile_rows: int = 0
    holdout_rows: int = 0
    positive_labels: int = 0
    neutral_labels: int = 0
    negative_labels: int = 0
    users_with_positive: int = 0
    users_with_negative: int = 0
    users_with_both: int = 0
    users_with_five_of_each: int = 0
    profile_tmdb_rows: int = 0
    holdout_tmdb_rows: int = 0
    users_with_complete_holdout_tmdb_mapping: int = 0
    users_with_strict_temporal_boundary: int = 0
    users_with_tied_temporal_boundary: int = 0
    users_with_activity_span_at_least_30_days: int = 0
    users_with_activity_span_at_least_365_days: int = 0
    users_strict_with_both_labels: int = 0
    users_strict_with_both_labels_and_30_day_span: int = 0
    users_strict_with_both_labels_and_365_day_span: int = 0
    users_analysis_ready_with_complete_tmdb_mapping: int = 0

    def add_user(
        self,
        *,
        profile: tuple[RatingRecord, ...],
        holdout: tuple[RatingRecord, ...],
        tmdb_movie_ids: set[int],
    ) -> None:
        positives = sum(item.rating >= POSITIVE_THRESHOLD for item in holdout)
        negatives = sum(item.rating <= NEGATIVE_THRESHOLD for item in holdout)
        neutrals = len(holdout) - positives - negatives
        profile_mapped = sum(item.movie_id in tmdb_movie_ids for item in profile)
        holdout_mapped = sum(item.movie_id in tmdb_movie_ids for item in holdout)
        activity_span_days = (
            max(item.timestamp for item in (*profile, *holdout))
            - min(item.timestamp for item in (*profile, *holdout))
        ) / 86400
        strict_boundary = profile[-1].timestamp < holdout[0].timestamp
        has_both_labels = positives > 0 and negatives > 0
        complete_holdout_mapping = holdout_mapped == len(holdout)

        self.eligible_users += 1
        self.profile_rows += len(profile)
        self.holdout_rows += len(holdout)
        self.positive_labels += positives
        self.neutral_labels += neutrals
        self.negative_labels += negatives
        self.users_with_positive += positives > 0
        self.users_with_negative += negatives > 0
        self.users_with_both += has_both_labels
        self.users_with_five_of_each += positives >= 5 and negatives >= 5
        self.profile_tmdb_rows += profile_mapped
        self.holdout_tmdb_rows += holdout_mapped
        self.users_with_complete_holdout_tmdb_mapping += complete_holdout_mapping
        self.users_with_strict_temporal_boundary += strict_boundary
        self.users_with_tied_temporal_boundary += not strict_boundary
        self.users_with_activity_span_at_least_30_days += activity_span_days >= 30
        self.users_with_activity_span_at_least_365_days += activity_span_days >= 365
        self.users_strict_with_both_labels += strict_boundary and has_both_labels
        self.users_strict_with_both_labels_and_30_day_span += (
            strict_boundary and has_both_labels and activity_span_days >= 30
        )
        analysis_ready = (
            strict_boundary and has_both_labels and activity_span_days >= 365
        )
        self.users_strict_with_both_labels_and_365_day_span += analysis_ready
        self.users_analysis_ready_with_complete_tmdb_mapping += (
            analysis_ready and complete_holdout_mapping
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "purpose": self.spec.purpose,
            "history_size": self.spec.history_size,
            "holdout_size": self.spec.holdout_size,
            "minimum_ratings": self.spec.minimum_ratings,
            "window_anchor": self.spec.window_anchor,
            "eligible_users": self.eligible_users,
            "label_rows": {
                "positive": self.positive_labels,
                "neutral": self.neutral_labels,
                "negative": self.negative_labels,
            },
            "eligible_user_coverage": {
                "with_positive": self.users_with_positive,
                "with_negative": self.users_with_negative,
                "with_positive_and_negative": self.users_with_both,
                "with_at_least_five_positive_and_five_negative": (
                    self.users_with_five_of_each
                ),
            },
            "tmdb_mapping": {
                "profile_rows": _coverage(self.profile_tmdb_rows, self.profile_rows),
                "holdout_rows": _coverage(self.holdout_tmdb_rows, self.holdout_rows),
                "users_with_complete_holdout_mapping": (
                    self.users_with_complete_holdout_tmdb_mapping
                ),
            },
            "temporal_coverage": {
                "users_with_strict_profile_holdout_boundary": (
                    self.users_with_strict_temporal_boundary
                ),
                "users_with_tied_profile_holdout_boundary": (
                    self.users_with_tied_temporal_boundary
                ),
                "users_with_window_span_at_least_30_days": (
                    self.users_with_activity_span_at_least_30_days
                ),
                "users_with_window_span_at_least_365_days": (
                    self.users_with_activity_span_at_least_365_days
                ),
                "users_with_strict_boundary_and_both_labels": (
                    self.users_strict_with_both_labels
                ),
                "users_with_strict_boundary_both_labels_and_30_day_span": (
                    self.users_strict_with_both_labels_and_30_day_span
                ),
                "users_with_strict_boundary_both_labels_and_365_day_span": (
                    self.users_strict_with_both_labels_and_365_day_span
                ),
                "analysis_ready_users_with_complete_holdout_tmdb_mapping": (
                    self.users_analysis_ready_with_complete_tmdb_mapping
                ),
            },
        }


@dataclass
class CensusState:
    cohorts: tuple[CohortSpec, ...]
    tmdb_movie_ids: set[int]
    movie_genres: dict[int, tuple[str, ...]]
    pilot_size: int
    pilot_seed: int
    total_users: int = 0
    total_ratings: int = 0
    invalid_rating_rows: int = 0
    invalid_timestamp_rows: int = 0
    nonpositive_timestamp_rows: int = 0
    user_order_anomalies: int = 0
    duplicate_user_movie_rows: int = 0
    duplicate_timestamp_rows: int = 0
    rating_rows_with_tmdb: int = 0
    rating_rows_with_movie_metadata: int = 0
    rating_rows_without_genres: int = 0
    rating_distribution: Counter[str] = field(default_factory=Counter)
    history_buckets: Counter[str] = field(default_factory=Counter)
    history_counts: list[int] = field(default_factory=list)
    rating_variances: list[float] = field(default_factory=list)
    activity_spans_days: list[float] = field(default_factory=list)
    activity_span_buckets: Counter[str] = field(default_factory=Counter)
    users_with_zero_activity_span: int = 0
    users_with_duplicate_timestamps: int = 0
    pilot_eligible_users: int = 0
    pilot_heap: list[tuple[int, int, dict[str, float | None]]] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.cohort_accumulators = {
            spec.name: CohortAccumulator(spec) for spec in self.cohorts
        }

    def process_user(self, user_id: int, rows: list[RatingRecord]) -> None:
        if not rows:
            return
        ordered = tuple(sorted(rows, key=lambda item: (item.timestamp, item.movie_id)))
        ratings = [item.rating for item in ordered]
        timestamps = [item.timestamp for item in ordered]
        count = len(ordered)

        self.total_users += 1
        self.history_counts.append(count)
        self.history_buckets[_history_bucket(count)] += 1
        self.rating_variances.append(statistics.pvariance(ratings))
        span_days = (max(timestamps) - min(timestamps)) / 86400
        self.activity_spans_days.append(span_days)
        self.activity_span_buckets[_activity_span_bucket(span_days)] += 1
        self.users_with_zero_activity_span += span_days == 0
        duplicate_timestamps = count - len(set(timestamps))
        self.duplicate_timestamp_rows += duplicate_timestamps
        self.users_with_duplicate_timestamps += duplicate_timestamps > 0

        for spec in self.cohorts:
            if count < spec.minimum_ratings:
                continue
            if spec.window_anchor == "start":
                profile_start = 0
                profile_end = spec.history_size
                holdout_end = spec.minimum_ratings
            else:
                profile_start = count - spec.minimum_ratings
                profile_end = count - spec.holdout_size
                holdout_end = count
            profile = ordered[profile_start:profile_end]
            holdout = ordered[profile_end:holdout_end]
            self.cohort_accumulators[spec.name].add_user(
                profile=profile,
                holdout=holdout,
                tmdb_movie_ids=self.tmdb_movie_ids,
            )
            if spec.name == "established":
                self._consider_pilot_user(user_id, profile, holdout)

    def _consider_pilot_user(
        self,
        user_id: int,
        profile: tuple[RatingRecord, ...],
        holdout: tuple[RatingRecord, ...],
    ) -> None:
        metrics = _genre_proxy_metrics(
            profile=profile,
            holdout=holdout,
            movie_genres=self.movie_genres,
        )
        if metrics is None:
            return
        self.pilot_eligible_users += 1
        key = _stable_sample_key(self.pilot_seed, user_id)
        entry = (-key, -user_id, metrics)
        if len(self.pilot_heap) < self.pilot_size:
            heapq.heappush(self.pilot_heap, entry)
            return
        if key < -self.pilot_heap[0][0]:
            heapq.heapreplace(self.pilot_heap, entry)

    def pilot_metrics(self) -> list[dict[str, float | None]]:
        return [entry[2] for entry in sorted(self.pilot_heap, reverse=True)]


def build_census(
    archive_path: Path,
    *,
    pilot_size: int = 2000,
    pilot_seed: int = PILOT_SEED,
    cohorts: tuple[CohortSpec, ...] = DEFAULT_COHORTS,
) -> dict[str, Any]:
    if pilot_size <= 0:
        raise ValueError("Pilot size must be positive.")
    if not archive_path.is_file():
        raise FileNotFoundError(f"MovieLens archive not found: {archive_path}")

    archive_sha256 = _file_hash(archive_path, "sha256")
    with ZipFile(archive_path) as archive:
        entries = _dataset_entries(archive)
        checksum_report = _checksum_report(archive, entries)
        movie_genres, movie_metadata_summary = _load_movie_genres(
            archive,
            entries["movies.csv"],
        )
        tmdb_movie_ids, link_summary = _load_tmdb_links(
            archive,
            entries["links.csv"],
        )
        state = CensusState(
            cohorts=cohorts,
            tmdb_movie_ids=tmdb_movie_ids,
            movie_genres=movie_genres,
            pilot_size=pilot_size,
            pilot_seed=pilot_seed,
        )
        _stream_ratings(archive, entries["ratings.csv"], state)

    pilot_summary = _pilot_summary(
        state.pilot_metrics(),
        state.pilot_eligible_users,
        pilot_seed=pilot_seed,
    )
    sample_sizes = _sample_size_options(pilot_summary)
    cohort_report = {
        name: accumulator.as_dict()
        for name, accumulator in state.cohort_accumulators.items()
    }
    return {
        "phase": "Recommendation Learning Lab: MovieLens 32M Census",
        "issue": 119,
        "report_date": REPORT_DATE,
        "command": "pnpm eval:movielens:census",
        "dataset": {
            "name": "MovieLens 32M",
            "source_url": SOURCE_URL,
            "generated_date": DATASET_GENERATED_DATE,
            "archive_path": _display_archive_path(archive_path),
            "archive_size_bytes": archive_path.stat().st_size,
            "archive_sha256": archive_sha256,
            "internal_checksums": checksum_report,
            "license_posture": {
                "allowed": "Research use under the MovieLens README conditions.",
                "commercial_constraint": (
                    "Commercial or revenue-bearing use requires GroupLens permission."
                ),
                "redistribution": (
                    "Do not publish raw files from this repository; preserve attribution "
                    "and source license conditions for any authorized redistribution."
                ),
            },
        },
        "summary": {
            "users": state.total_users,
            "ratings": state.total_ratings,
            "mean_ratings_per_user": _round(
                state.total_ratings / state.total_users if state.total_users else 0
            ),
            "movie_rows": movie_metadata_summary["movie_rows"],
            "movies_with_tmdb_id": link_summary["movies_with_tmdb_id"],
        },
        "user_history": {
            "buckets": dict(_ordered_history_buckets(state.history_buckets)),
            "quantiles": _quantiles(state.history_counts),
        },
        "ratings": {
            "distribution": dict(sorted(state.rating_distribution.items())),
            "user_rating_variance_quantiles": _quantiles(state.rating_variances),
            "activity_span_days_quantiles": _quantiles(state.activity_spans_days),
            "activity_span_buckets": dict(
                _ordered_activity_span_buckets(state.activity_span_buckets)
            ),
            "users_with_zero_activity_span": state.users_with_zero_activity_span,
            "users_with_duplicate_timestamps": state.users_with_duplicate_timestamps,
        },
        "metadata_coverage": {
            **movie_metadata_summary,
            **link_summary,
            "rating_rows_with_movie_metadata": _coverage(
                state.rating_rows_with_movie_metadata,
                state.total_ratings,
            ),
            "rating_rows_with_tmdb_id": _coverage(
                state.rating_rows_with_tmdb,
                state.total_ratings,
            ),
            "rating_rows_without_genres": _coverage(
                state.rating_rows_without_genres,
                state.total_ratings,
            ),
        },
        "anomalies": {
            "invalid_rating_rows": state.invalid_rating_rows,
            "invalid_timestamp_rows": state.invalid_timestamp_rows,
            "nonpositive_timestamp_rows": state.nonpositive_timestamp_rows,
            "user_order_anomalies": state.user_order_anomalies,
            "duplicate_user_movie_rows": state.duplicate_user_movie_rows,
            "duplicate_timestamp_rows_within_user": state.duplicate_timestamp_rows,
        },
        "cohort_candidates": cohort_report,
        "exploration_variance_pilot": pilot_summary,
        "sample_size_options": sample_sizes,
        "protocol_recommendation": {
            "status": "proposal_for_issue_120_founder_gate",
            "main_cohort": (
                "Use established users with the immediately preceding 100 ratings as "
                "profile evidence and the final 30 ratings as a fixed future window."
            ),
            "deep_history_cohort": (
                "Report 500-history plus 50-future users separately for richer feature "
                "experiments; do not let prolific users dominate the main estimate."
            ),
            "cold_start_cohort": (
                "Use each user's earliest 10 ratings as history and next 10 as future "
                "labels. Treat this as a limited calibration diagnostic because strict, "
                "long-span eligibility is much smaller than the full dataset."
            ),
            "sparse_recent_profile_cohort": (
                "Use the 10 ratings immediately before a final 10-rating window to test "
                "limited visible evidence at a mature point, and do not call it true "
                "cold start."
            ),
            "sample_size": (
                "Select the final user count in Issue 120 from the declared minimum "
                "useful effect and the conservative or pilot-based table. Re-estimate "
                "paired-difference variance after real baseline results exist."
            ),
            "temporal_rule": (
                "Preserve per-user chronology now and add a global time boundary before "
                "training collaborative models across users and movies."
            ),
            "sealed_data_rule": (
                "Issue 119 uses exploration data only. Validation and sealed manifests "
                "are created only after the founder locks the protocol in Issue 120."
            ),
        },
        "evidence_limits": [
            "The genre proxy pilot estimates metric scale, not V1/V2 paired-difference variance.",
            "Many users batch-record ratings, so rating timestamps are not guaranteed watch timestamps.",
            "MovieLens ratings do not represent tonight intent, streaming availability, or couple negotiation.",
            "Selecting only prolific users would improve per-user stability while reducing product representativeness.",
            "Unrated movies remain unknown and are not counted as dislikes.",
            "The census does not tune or promote any scorer.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# MovieLens 32M Census And Protocol Recommendation",
        "",
        f"Date: {report['report_date']}",
        f"Phase: {report['phase']}",
        f"GitHub issue: #{report['issue']}",
        f"Command: `{report['command']}`",
        "",
        "## Engineering Evidence Loop",
        "",
        "- Claim: Benchmark sizing and cohort rules can come from measured corpus properties rather than guessed percentages.",
        "- Contract: This JSON and Markdown pair records provenance, integrity, cohort eligibility, label balance, mapping, anomalies, pilot variance, and sample-size options.",
        "- Boundary: Offline evaluation tooling and ignored local data only; no production scorer path changes.",
        "- Behavior: The same archive, cohort definitions, pilot size, and seed reproduce the same report.",
        "- Evidence: Internal file checksums, full-corpus counts, deterministic cohort windows, and an exploration-only variance proxy.",
        "- Decision: Issue #120 must approve or revise the proposal before manifests, model tuning, or sealed testing begin.",
        "",
        "## Dataset Summary",
        "",
        f"- Users: {summary['users']:,}",
        f"- Ratings: {summary['ratings']:,}",
        f"- Mean ratings per user: {summary['mean_ratings_per_user']}",
        f"- Movie rows: {summary['movie_rows']:,}",
        f"- Movies with TMDb IDs: {summary['movies_with_tmdb_id']:,}",
        f"- Archive SHA-256: `{report['dataset']['archive_sha256']}`",
        f"- Internal checksum status: {report['dataset']['internal_checksums']['status']}",
        "",
        "## License Posture",
        "",
        f"- Research use: {report['dataset']['license_posture']['allowed']}",
        f"- Commercial constraint: {report['dataset']['license_posture']['commercial_constraint']}",
        f"- Repository rule: {report['dataset']['license_posture']['redistribution']}",
        "",
        "## User History Depth",
        "",
        "| Ratings per user | Users |",
        "|---|---:|",
    ]
    for bucket, count in report["user_history"]["buckets"].items():
        lines.append(f"| {bucket} | {count:,} |")

    lines.extend(
        [
            "",
            "## Candidate Cohorts",
            "",
            "| Cohort | Window | History | Future | Eligible users | Strict + both labels | Strict + both + 365 days | Analysis-ready + mapped | Holdout TMDb coverage |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name, cohort in report["cohort_candidates"].items():
        tmdb = cohort["tmdb_mapping"]["holdout_rows"]
        temporal = cohort["temporal_coverage"]
        lines.append(
            "| "
            + " | ".join(
                [
                    name,
                    cohort["window_anchor"],
                    f"{cohort['history_size']:,}",
                    f"{cohort['holdout_size']:,}",
                    f"{cohort['eligible_users']:,}",
                    f"{temporal['users_with_strict_boundary_and_both_labels']:,}",
                    f"{temporal['users_with_strict_boundary_both_labels_and_365_day_span']:,}",
                    f"{temporal['analysis_ready_users_with_complete_holdout_tmdb_mapping']:,}",
                    _percent_text(tmdb["rate"]),
                ]
            )
            + " |"
        )

    coverage = report["metadata_coverage"]
    anomalies = report["anomalies"]
    lines.extend(
        [
            "",
            "## Coverage And Anomalies",
            "",
            f"- Rating rows with TMDb ID: {_coverage_text(coverage['rating_rows_with_tmdb_id'])}",
            f"- Rating rows with movie metadata: {_coverage_text(coverage['rating_rows_with_movie_metadata'])}",
            f"- Rating rows without genres: {_coverage_text(coverage['rating_rows_without_genres'])}",
            f"- Invalid rating rows: {anomalies['invalid_rating_rows']:,}",
            f"- Invalid timestamps: {anomalies['invalid_timestamp_rows']:,}",
            f"- Nonpositive timestamps: {anomalies['nonpositive_timestamp_rows']:,}",
            f"- Duplicate user-movie rows: {anomalies['duplicate_user_movie_rows']:,}",
            f"- User-order anomalies: {anomalies['user_order_anomalies']:,}",
            f"- Duplicate timestamps within a user: {anomalies['duplicate_timestamp_rows_within_user']:,}",
            f"- Users with at least one duplicate timestamp: {report['ratings']['users_with_duplicate_timestamps']:,}",
            "",
            "## Exploration-Only Variance Pilot",
            "",
            f"- Method: {report['exploration_variance_pilot']['method']}",
            f"- Eligible established users considered: {report['exploration_variance_pilot']['eligible_users_considered']:,}",
            f"- Deterministic sample size: {report['exploration_variance_pilot']['sample_size']:,}",
            "",
            "| Metric | Users | Mean | Standard deviation |",
            "|---|---:|---:|---:|",
        ]
    )
    for name, metric in report["exploration_variance_pilot"]["metrics"].items():
        lines.append(
            f"| {name} | {metric['count']:,} | {metric['mean']:.4f} | "
            f"{metric['standard_deviation']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Sample-Size Options",
            "",
            "These are two-sided 95% planning estimates with 80% power for independent user-level observations.",
            "The conservative column uses standard deviation 0.5.",
            "The proxy columns use the exploration genre baseline and must be replaced by paired model-difference variance once it exists.",
            "",
            "| Minimum effect | Conservative users | NDCG@5 proxy | Pairwise proxy | Dislike@5 proxy |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for option in report["sample_size_options"]:
        estimates = option["estimated_users"]
        lines.append(
            f"| {_percent_text(option['minimum_effect'])} | "
            f"{estimates['conservative']:,} | "
            f"{estimates.get('ndcg_at_5', 0):,} | "
            f"{estimates.get('pairwise_accuracy', 0):,} | "
            f"{estimates.get('known_dislike_rate_at_5', 0):,} |"
        )

    recommendation = report["protocol_recommendation"]
    lines.extend(
        [
            "",
            "## Protocol Recommendation For Issue #120",
            "",
            f"- Main cohort: {recommendation['main_cohort']}",
            f"- Deep-history cohort: {recommendation['deep_history_cohort']}",
            f"- Cold-start cohort: {recommendation['cold_start_cohort']}",
            f"- Sparse recent-profile cohort: {recommendation['sparse_recent_profile_cohort']}",
            f"- Sample size: {recommendation['sample_size']}",
            f"- Temporal rule: {recommendation['temporal_rule']}",
            f"- Sealed-data rule: {recommendation['sealed_data_rule']}",
            "",
            "## Evidence Limits",
            "",
        ]
    )
    lines.extend(f"- {limit}" for limit in report["evidence_limits"])
    lines.append("")
    return "\n".join(lines)


def _dataset_entries(archive: ZipFile) -> dict[str, str]:
    required = (
        "ratings.csv",
        "movies.csv",
        "links.csv",
        "tags.csv",
        "checksums.txt",
    )
    names = archive.namelist()
    entries = {}
    for filename in required:
        matches = [name for name in names if name.endswith(f"/{filename}")]
        if len(matches) != 1:
            raise ValueError(f"Expected one {filename} entry, found {len(matches)}.")
        entries[filename] = matches[0]
    return entries


def _checksum_report(archive: ZipFile, entries: dict[str, str]) -> dict[str, Any]:
    raw = archive.read(entries["checksums.txt"]).decode("utf-8")
    expected = {}
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            expected[parts[-1].lstrip("*")] = parts[0].lower()
    files = {}
    for filename in ("ratings.csv", "movies.csv", "links.csv", "tags.csv"):
        digest = hashlib.md5(usedforsecurity=False)
        with archive.open(entries[filename]) as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        files[filename] = {
            "expected_md5": expected.get(filename),
            "actual_md5": actual,
            "matches": expected.get(filename) == actual,
        }
    return {
        "status": "passed" if all(item["matches"] for item in files.values()) else "failed",
        "files": files,
    }


def _load_movie_genres(
    archive: ZipFile,
    entry: str,
) -> tuple[dict[int, tuple[str, ...]], dict[str, int]]:
    genres_by_movie = {}
    no_genres = 0
    with_genres = 0
    with archive.open(entry) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        for row in reader:
            movie_id = int(row["movieId"])
            genres = tuple(
                genre
                for genre in row["genres"].split("|")
                if genre and genre != "(no genres listed)"
            )
            genres_by_movie[movie_id] = genres
            if genres:
                with_genres += 1
            else:
                no_genres += 1
    return genres_by_movie, {
        "movie_rows": len(genres_by_movie),
        "movies_with_genres": with_genres,
        "movies_without_genres": no_genres,
    }


def _load_tmdb_links(
    archive: ZipFile,
    entry: str,
) -> tuple[set[int], dict[str, int]]:
    movie_ids = set()
    link_rows = 0
    with archive.open(entry) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        for row in reader:
            link_rows += 1
            if (row.get("tmdbId") or "").strip():
                movie_ids.add(int(row["movieId"]))
    return movie_ids, {
        "link_rows": link_rows,
        "movies_with_tmdb_id": len(movie_ids),
        "movies_without_tmdb_id": link_rows - len(movie_ids),
    }


def _stream_ratings(archive: ZipFile, entry: str, state: CensusState) -> None:
    current_user_id: int | None = None
    current_rows: list[RatingRecord] = []
    current_movie_ids: set[int] = set()
    with archive.open(entry) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        for row in reader:
            try:
                user_id = int(row["userId"])
                movie_id = int(row["movieId"])
                rating = float(row["rating"])
            except (KeyError, TypeError, ValueError):
                state.invalid_rating_rows += 1
                continue
            try:
                timestamp = int(row["timestamp"])
            except (KeyError, TypeError, ValueError):
                state.invalid_timestamp_rows += 1
                continue
            if timestamp <= 0:
                state.nonpositive_timestamp_rows += 1

            if current_user_id is None:
                current_user_id = user_id
            if user_id != current_user_id:
                state.process_user(current_user_id, current_rows)
                if user_id < current_user_id:
                    state.user_order_anomalies += 1
                current_user_id = user_id
                current_rows = []
                current_movie_ids = set()

            state.total_ratings += 1
            state.rating_distribution[f"{rating:.1f}"] += 1
            state.rating_rows_with_tmdb += movie_id in state.tmdb_movie_ids
            state.rating_rows_with_movie_metadata += movie_id in state.movie_genres
            state.rating_rows_without_genres += not state.movie_genres.get(movie_id)
            if movie_id in current_movie_ids:
                state.duplicate_user_movie_rows += 1
            current_movie_ids.add(movie_id)
            current_rows.append(
                RatingRecord(movie_id=movie_id, rating=rating, timestamp=timestamp)
            )

    if current_user_id is not None:
        state.process_user(current_user_id, current_rows)


def _genre_proxy_metrics(
    *,
    profile: tuple[RatingRecord, ...],
    holdout: tuple[RatingRecord, ...],
    movie_genres: dict[int, tuple[str, ...]],
) -> dict[str, float | None] | None:
    genre_totals: Counter[str] = Counter()
    genre_counts: Counter[str] = Counter()
    for item in profile:
        for genre in movie_genres.get(item.movie_id, ()):
            genre_totals[genre] += (item.rating - 3.0) / 2.0
            genre_counts[genre] += 1
    if not genre_counts:
        return None

    genre_affinity = {
        genre: genre_totals[genre] / count for genre, count in genre_counts.items()
    }
    scored = []
    for item in holdout:
        genres = movie_genres.get(item.movie_id, ())
        score = (
            sum(genre_affinity.get(genre, 0.0) for genre in genres) / len(genres)
            if genres
            else 0.0
        )
        scored.append((score, item.movie_id, item.rating))
    ranked = sorted(scored, key=lambda item: (-item[0], item[1]))
    positives = [item for item in ranked if item[2] >= POSITIVE_THRESHOLD]
    negatives = [item for item in ranked if item[2] <= NEGATIVE_THRESHOLD]

    pairwise_accuracy = None
    if positives and negatives:
        points = 0.0
        pairs = 0
        for positive in positives:
            for negative in negatives:
                pairs += 1
                if positive[0] > negative[0]:
                    points += 1
                elif positive[0] == negative[0]:
                    points += 0.5
        pairwise_accuracy = points / pairs

    return {
        "ndcg_at_5": _ndcg_at_k(ranked, 5),
        "pairwise_accuracy": pairwise_accuracy,
        "known_dislike_rate_at_5": (
            sum(item[2] <= NEGATIVE_THRESHOLD for item in ranked[:5])
            / max(1, len(ranked[:5]))
        ),
    }


def _ndcg_at_k(ranked: list[tuple[float, int, float]], k: int) -> float:
    relevances = [_relevance(item[2]) for item in ranked]
    ideal = sorted(relevances, reverse=True)
    ideal_dcg = _dcg(ideal[:k])
    if ideal_dcg == 0:
        return 0.0
    return _dcg(relevances[:k]) / ideal_dcg


def _relevance(rating: float) -> float:
    return max(0.0, rating - 2.5)


def _dcg(relevances: Iterable[float]) -> float:
    return sum(
        ((2**relevance) - 1) / math.log2(index + 2)
        for index, relevance in enumerate(relevances)
    )


def _pilot_summary(
    metrics: list[dict[str, float | None]],
    eligible_users_considered: int,
    *,
    pilot_seed: int,
) -> dict[str, Any]:
    names = ("ndcg_at_5", "pairwise_accuracy", "known_dislike_rate_at_5")
    summaries = {}
    for name in names:
        values = [float(item[name]) for item in metrics if item[name] is not None]
        summaries[name] = {
            "count": len(values),
            "mean": _round(statistics.fmean(values) if values else 0.0, 6),
            "variance": _round(statistics.variance(values) if len(values) > 1 else 0.0, 6),
            "standard_deviation": _round(
                statistics.stdev(values) if len(values) > 1 else 0.0,
                6,
            ),
            "quantiles": _quantiles(values),
        }
    return {
        "method": (
            "Deterministic established-user sample scored by a simple profile-genre "
            "content proxy. This estimates user-level metric scale, not model-delta variance."
        ),
        "seed": pilot_seed,
        "eligible_users_considered": eligible_users_considered,
        "sample_size": len(metrics),
        "metrics": summaries,
    }


def _sample_size_options(pilot_summary: dict[str, Any]) -> list[dict[str, Any]]:
    options = []
    for effect in SAMPLE_EFFECTS:
        estimates = {"conservative": _required_users(0.5, effect)}
        for name, summary in pilot_summary["metrics"].items():
            estimates[name] = _required_users(summary["standard_deviation"], effect)
        options.append(
            {
                "minimum_effect": effect,
                "confidence_level": 0.95,
                "power": 0.80,
                "estimated_users": estimates,
            }
        )
    return options


def _required_users(standard_deviation: float, effect: float) -> int:
    if standard_deviation <= 0:
        return 2
    return max(
        2,
        math.ceil(
            (((Z_95_TWO_SIDED + Z_80_POWER) * standard_deviation) / effect)
            ** 2
        ),
    )


def _stable_sample_key(seed: int, user_id: int) -> int:
    payload = f"{seed}:{user_id}".encode("ascii")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _history_bucket(count: int) -> str:
    if count < 20:
        return "under 20"
    if count < 50:
        return "20-49"
    if count < 100:
        return "50-99"
    if count < 200:
        return "100-199"
    if count < 500:
        return "200-499"
    if count < 1000:
        return "500-999"
    return "1000+"


def _activity_span_bucket(span_days: float) -> str:
    if span_days == 0:
        return "zero span"
    if span_days <= 1:
        return "up to 1 day"
    if span_days < 30:
        return "1-29 days"
    if span_days < 365:
        return "30-364 days"
    if span_days < 1825:
        return "1-5 years"
    return "5+ years"


def _ordered_history_buckets(counter: Counter[str]):
    for name in ("under 20", "20-49", "50-99", "100-199", "200-499", "500-999", "1000+"):
        if counter[name]:
            yield name, counter[name]


def _ordered_activity_span_buckets(counter: Counter[str]):
    for name in (
        "zero span",
        "up to 1 day",
        "1-29 days",
        "30-364 days",
        "1-5 years",
        "5+ years",
    ):
        if counter[name]:
            yield name, counter[name]


def _quantiles(values: Iterable[float | int]) -> dict[str, float]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {name: 0.0 for name in ("min", "p25", "p50", "p75", "p90", "p95", "p99", "max")}
    return {
        "min": _round(ordered[0]),
        "p25": _round(_percentile(ordered, 0.25)),
        "p50": _round(_percentile(ordered, 0.50)),
        "p75": _round(_percentile(ordered, 0.75)),
        "p90": _round(_percentile(ordered, 0.90)),
        "p95": _round(_percentile(ordered, 0.95)),
        "p99": _round(_percentile(ordered, 0.99)),
        "max": _round(ordered[-1]),
    }


def _percentile(ordered: list[float], percentile: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    position = percentile * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _coverage(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "count": numerator,
        "total": denominator,
        "rate": _round(numerator / denominator if denominator else 0.0, 6),
    }


def _coverage_text(coverage: dict[str, Any]) -> str:
    return (
        f"{coverage['count']:,} / {coverage['total']:,} "
        f"({_percent_text(coverage['rate'])})"
    )


def _percent_text(value: float) -> str:
    return f"{value * 100:.2f}%"


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def _file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_archive_path(path: Path) -> str:
    parts = path.parts
    if ".tools" in parts:
        return Path(*parts[parts.index(".tools") :]).as_posix()
    return path.name


def write_reports(
    report: dict[str, Any],
    *,
    json_path: Path,
    markdown_path: Path,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    markdown_path.write_text(render_markdown(report))
