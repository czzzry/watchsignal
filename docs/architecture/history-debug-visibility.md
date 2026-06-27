# History And Debug Visibility

## Purpose

History and debug visibility exists so the founder can trust, inspect, and improve the recommender.
The MVP should answer two different questions.
The first question is user-facing history: what happened in recent movie-night sessions.
The second question is debug visibility: why the app ranked or filtered titles the way it did.

## MVP Exposure

The MVP history view should expose recent sessions, their final recommendation, the reranked shortlist, the selected outcome, and post-watch feedback when present.
The MVP debug view should expose the candidate inputs, Safe Pick status, hard-filter result, per-person scores, group score, fit bucket, and short explanation that existed at recommendation time.
The debug view may also show onboarding completeness, watched-history records, manual backfill records, and whether free-text feedback exists.
The debug view should not interpret free-text feedback with an LLM in MVP.
The debug view should not expose API keys, environment variables, raw secrets, or private notes in committed examples.

## Snapshot Shape

The backend can build a read-only session debug snapshot from existing domain records.
The current helper lives in `apps/api/src/movie_night_mediator/app/debug_history.py`.
The rich scoring snapshot helper does not persist anything.
It combines a scoring request, recommendation result, shortlist reactions, post-watch feedback, and watched-history backfill records into a stable inspection shape.
The MVP API route is narrower because the current SQLite stores do not persist the original scoring request or recommendation result snapshot.
`GET /debug/history/sessions/{session_id}` returns the persisted shared-session evidence that exists after a local session.
That evidence includes session state, shortlist titles and ranks, participant reactions, reranked source movie ids, best pick id, post-watch feedback labels, and whether a feedback note exists.
The route also returns `recommendationSnapshot` when a ranking snapshot has been saved for the session.
That snapshot contains ranked candidate ids and titles, ranks, group score, per-user scores, short ranking explanation, hard-filter pass value, fit bucket, Interesting Safe Pick flag, uncertainty reason, recommended follow-up, and interesting safe-pick id.
The route still returns `unavailableEvidence` so callers can see whether the original scoring request and raw candidate inputs are absent.
When no recommendation snapshot has been saved, the route continues to mark candidate inputs, hard-filter results, per-person scores, group scores, fit buckets, and Safe Pick flags as unavailable.
The route is read-only and local-debug oriented.
The pass-the-phone web UI exposes this route from the results screen through a compact current-session evidence panel.
That panel is intentionally diagnostic rather than dashboard-like.
It uses the Next proxy at `apps/web/app/api/session/[sessionId]/debug-history/route.ts` so the browser does not need to know the backend base URL.
Demo-mode sessions and failed debug fetches show local explanatory messages instead of interrupting the result flow.

## Persisted Recommendation Snapshot

Recommendation snapshots are owned by the backend recommendation and storage layer.
The domain shape lives in `apps/api/src/movie_night_mediator/domain/models.py`.
The SQLite store lives in `apps/api/src/movie_night_mediator/storage/recommendation_snapshot.py`.
The service helper lives in `apps/api/src/movie_night_mediator/app/recommendation_snapshot.py`.
The service builds a snapshot from an existing `ScoringRequest` and `RecommendationResult`.
It intentionally copies the scorer output rather than recalculating or changing any scoring formula.
The fixture candidate adapter can receive that snapshot service when generating an offline shortlist so backend fixture recommendations persist their ranking evidence automatically.
Each save replaces the previous snapshot for the same session id.
This keeps history explainable at the moment of ranking while allowing a later recommendation run to overwrite the session snapshot deliberately.
The current snapshot does not persist the full scoring request, full candidate metadata, providers, genres, watched-history inputs, or raw private notes.
Those remain future follow-up fields if the founder wants deeper auditability.

```mermaid
flowchart LR
    A["Scoring request"] --> E["Debug snapshot"]
    B["Recommendation result"] --> E
    C["Shortlist reactions"] --> E
    D["Outcome and feedback"] --> E
    F["Watched history and backfill"] --> E
    E --> G["Local-only history/debug API"]
    G --> H["Future lightweight phone or admin view"]
```

## Constraints

History and debug visibility must be local-only for MVP.
Committed fixtures may use public movie metadata and generic profile labels.
Committed fixtures must not include real household watch history, ratings, free-text notes, or identifiers.
The first implementation should prefer read models over schema changes when the underlying session and feedback stores already contain the data.
Any API route should be read-only unless a later issue explicitly owns outcome, feedback, or backfill writes.

## Non-Goals

This slice does not build UI polish.
This slice does not add LLM interpretation.
This slice does not change scoring weights.
This slice does not introduce analytics dashboards.
This slice does not require TMDb live calls.
This slice does not change n8n behavior or documentation.

## Future Notes

MVP plus 1 can add LLM summaries of free-text feedback after the raw notes are safely stored and inspectable.
Future recommender evaluation can use debug snapshots as test-case evidence for comparing scoring changes against fixed datasets.
A future test-data validation agent could assemble synthetic or public-profile-like scoring cases and check whether scorer changes improve predicted likes without degrading Safe Pick behavior.
That future work should remain separate from the MVP history view so the couch flow stays small and useful.
