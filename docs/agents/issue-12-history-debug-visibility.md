# Issue 12 - History And Debug Visibility

## Objective

Add lightweight local visibility into recent sessions, outcomes, reactions, stored history, and recommendation debug evidence.
The goal is to help the founder understand whether the app is learning and why a recommendation happened.

## Current Preparation

The architecture note is `docs/architecture/history-debug-visibility.md`.
The read-only helper is `apps/api/src/movie_night_mediator/app/debug_history.py`.
The helper can build a debug snapshot from existing scoring, reaction, feedback, and watched-history domain records.
It intentionally does not add persistence schemas or API route wiring.

## MVP Behavior To Expose

Recent sessions should be listable once session persistence exists.
A session detail should show the original shortlist, reranked shortlist, reactions by participant, final pick, outcome, post-watch feedback, and relevant watched-history records.
The debug detail should show Safe Pick status, already-watched status, provider access summary, hard-filter result, fit bucket, per-person scores, group score, and `why_short`.
The detail should show whether free-text notes exist without using an LLM to interpret them in MVP.

## Owned Areas For The Implementation Worker

- `apps/api/src/movie_night_mediator/app/debug_history.py`
- history or debug read-service modules
- history or debug route models and tests, if API wiring is explicitly in scope
- docs under `docs/architecture/` and `docs/agents/`

## Off-Limits Areas

- scoring formula changes
- TMDb live adapter behavior
- household setup changes
- onboarding writes
- outcome or feedback writes unless Issue 10 has landed and this issue is only reading from it
- n8n project files

## Dependencies

Issue 12 depends on shared session persistence from Slice 8.
Issue 12 depends on outcome and post-watch feedback persistence from Slice 10.
Manual backfill from Slice 11 is useful but should not block a first session-detail debug view.

## Acceptance Criteria

- [ ] Recent sessions can be listed from local persistence.
- [ ] A session detail can show shortlist, reactions, final pick, outcome, and feedback when present.
- [ ] A debug snapshot can explain each ranked candidate using existing scoring evidence.
- [ ] The implementation does not expose secrets or committed real household data.
- [ ] Tests cover the read model or service behavior behind the view.
- [ ] The learning artifact explains user-facing history versus internal debug evidence.

## Validation

Run focused API tests for any added helper, read service, or route.
Run the API compile check after backend code changes.
Run the web production build only if a UI view is touched.

## Future Notes

MVP plus 1 can add LLM summaries of free-text feedback.
Future recommender experiments can use fixed debug snapshots as regression cases for scoring changes.
That evaluation work should be a separate issue because it is research infrastructure, not the MVP couch history view.
