# PRD - Taste Lab

## Problem Statement

WatchSignal needs better taste signal before it can produce meaningfully personal recommendations.
The founder is willing to provide many movie ratings if those ratings are useful.
The risk is not rating effort by itself.
The risk is wasting effort on arbitrary movies that do not teach the system much.

The core question is whether WatchSignal can choose movies with high preference-information value.
If it can, the founder can rapidly build a useful taste profile without pretending that a handful of vague onboarding prompts are enough.

Taste Lab should start as a private calibration tool.
It may live outside the polished couch-flow app at first.
It must still produce structured data that can later be imported into WatchSignal or folded into the app itself.

## MVP Plus 1 Outcome Amendment

The MVP plus 1 outcome is not that Taste Lab exists as a standalone mini-app.
The MVP plus 1 outcome is that a user can use Taste Lab and have their tastes updated in WatchSignal.

Taste Lab should remain private and optional for now.
Its ratings must still become durable WatchSignal taste data.
The normal couch-flow app should be able to benefit from those signals without requiring Taste Lab itself to become part of the main user flow.

The minimum outcome improvement is:

> As a user, I can use Taste Lab and have my tastes updated to the WatchSignal app.

This means the next work should prioritize the data path from Taste Lab to WatchSignal recommendations.
The private Taste Lab route is only the input tool.
The product win is that WatchSignal recommendations become visibly or explainably influenced by saved Taste Lab signals.

## Solution

Build Taste Lab as a research-backed rapid rating loop.
Taste Lab selects movies that are expected to reveal taste boundaries faster than random or popularity-only selection.
The founder rates batches of 10 movies with simple labels.
The system saves those labels as durable taste signals.
The queue excludes already-rated movies, deprioritizes movies marked `Haven't seen`, and refreshes with more high-signal candidates.

The first implementation should be deliberately modest.
It should prove the queue-generation theory before investing in a polished UI.
The system should be usable as a standalone tool, but all data contracts should be compatible with future WatchSignal ingestion.

After the private rating loop works, the next implementation step is the payoff loop.
Taste Lab ratings should feed a shared taste-profile read model.
Recommendation scoring should read that model as an additive signal alongside onboarding, session reactions, watched-history backfill, and post-watch feedback.
Taste Lab should not directly own the couch flow.

## User Stories

1. As the founder, I want a fast way to rate many movies, so that WatchSignal can learn my taste without relying on a tiny onboarding sample.
2. As the founder, I want the movies I rate to be selected for signal value, so that my effort is not wasted on arbitrary popular titles.
3. As the founder, I want to rate movies in batches of 10, so that I can quickly get into a rhythm.
4. As the founder, I want to mark `Loved`, `Liked`, `Meh`, `Hated`, or `Haven't seen`, so that the system captures both preference and familiarity.
5. As the founder, I want `Haven't seen` to be stored separately from dislike, so that unseen movies do not poison my taste profile.
6. As the founder, I want already-rated movies excluded from future batches, so that I do not waste time repeating ratings.
7. As the founder, I want unseen movies deprioritized for a while, so that the queue stays answerable.
8. As the founder, I want the queue to include recognizable movies, so that I can answer quickly.
9. As the founder, I want the queue to include divisive or taste-separating movies, so that the system learns my boundaries.
10. As the founder, I want the queue to cover many genres and tones, so that the taste profile does not overfit to one kind of movie.
11. As the founder, I want the queue to avoid near-duplicates, so that each batch teaches the system something new.
12. As the founder, I want real poster art and metadata, so that rating is fast and visually recognizable.
13. As the founder, I want progress visibility, so that I know how much signal I have added.
14. As the founder, I want coverage visibility, so that I can tell whether my profile is narrow or broad.
15. As the founder, I want a way to export Taste Lab ratings, so that they can be imported into WatchSignal.
16. As the founder, I want Taste Lab to remain private by default, so that personal taste data is not accidentally published.
17. As the founder, I want the first queue-generation method to be documented, so that future recommender changes are evidence-based.
18. As the founder, I want to compare high-signal rating against popularity-only rating, so that we know whether the hypothesis works.
19. As the founder, I want the system to admit if the signal score is not yet proven, so that we do not confuse research with fact.
20. As the founder, I want a ranked list of candidate signal movies before UI work begins, so that we can inspect whether the generated queue feels sane.
21. As a future WatchSignal user, I want Taste Lab data to improve recommendations, so that my previous calibration effort pays off during movie night.
22. As a future WatchSignal user, I want Taste Lab to stay optional, so that the main couch flow does not become homework.
23. As a future WatchSignal user, I want the app to learn from both Taste Lab ratings and real session behavior, so that the profile improves over time.
24. As a future WatchSignal user, I want each person's Taste Lab data kept separate, so that the couple profile does not blur individual preferences.
25. As a future WatchSignal user, I want overlap calibration to use both people's taste signals, so that recommendations target shared enjoyment rather than one person's taste alone.
26. As a WatchSignal user, I want Taste Lab ratings to update my WatchSignal taste profile, so that calibration effort improves the main app.
27. As a WatchSignal user, I want recommendations to be influenced by my saved Taste Lab signals, so that the app reflects what it learned from calibration.
28. As the founder, I want tests or evaluation output that prove Taste Lab data reaches recommendation inputs, so that MVP plus 1 is an outcome improvement rather than a separate tool.

## Implementation Decisions

- Taste Lab starts as a private research and tooling lane, not a polished public app feature.
- Taste Lab must produce a stable export/import contract so WatchSignal can ingest its ratings later.
- The first data substrate should be MovieLens-style ratings data.
- TMDb should remain the display/artwork substrate for posters and public movie metadata.
- The first signal-score formula should be simple, inspectable, and documented.
- The first signal-score formula should include recognizability, response probability, divisiveness, discrimination proxy, coverage, and non-redundancy.
- `Haven't seen` is a familiarity signal, not a negative taste signal.
- Taste labels should map cleanly into existing WatchSignal taste language where possible.
- `Loved` and `Liked` are positive taste signals with different strength.
- `Meh` is weak or neutral preference, not the same as missing data.
- `Hated` is a strong negative preference signal.
- Ratings should store source movie id, title, release year, display metadata, label, profile id, timestamp, and source of the queue.
- Queue candidates should store enough score components to explain why they were selected.
- The initial queue generator should be offline and reproducible.
- The first UI can be private and utilitarian, but should use real poster art.
- The main WatchSignal couch flow should not depend on Taste Lab being complete.
- The import path should be additive, so Taste Lab ratings enrich taste data without overwriting existing session feedback.
- The long-term architecture should allow Taste Lab to become either an internal WatchSignal route or remain a standalone calibration tool.
- Taste Lab should remain outside the normal couch-flow UI until its recommendation payoff is proven.
- Taste Lab ratings should feed WatchSignal through a shared taste-profile read model, not through direct coupling between the private route and couch flow.
- Recommendation scoring should treat Taste Lab ratings as durable profile-level evidence.
- The app should be able to explain, at least minimally, when saved taste data influenced a recommendation.

## Testing Decisions

- Tests should verify externally visible behavior and data contracts rather than exact internal scoring weights.
- The offline queue generator should be tested with a tiny fixture dataset that proves the feature calculations and ranking shape.
- The export/import contract should be tested as a stable schema.
- The storage layer should be tested for duplicate prevention, label persistence, and `Haven't seen` handling.
- The queue API should be tested for excluding already-rated movies and returning a stable batch size when enough candidates exist.
- The first evaluation test should compare at least two strategies, such as popularity-only and hybrid signal score, on a controlled fixture.
- UI tests can wait until the private Taste Lab route exists.
- Recommendation-quality claims should require an evaluation harness or a recorded founder review, not only implementation confidence.
- Tests should prove that Taste Lab ratings can be read as WatchSignal taste-profile inputs.
- Tests should prove that at least one fixed recommendation scenario changes or is explainably influenced when Taste Lab-derived signals are present.

## Out of Scope

- Public Taste Lab launch.
- Polished Taste Lab visual design in the first research slice.
- Paid recommendation vendors.
- LLM ranking authority.
- Importing private Letterboxd, IMDb, or streaming-account data in the first slice.
- Publishing GitHub issues without explicit founder approval.
- Replacing the existing WatchSignal scoring module in the first slice.
- Building a complete collaborative-filtering recommender before the offline signal-score spike proves useful.
- Making Taste Lab a required step in the main couch-flow app.
- Polishing Taste Lab as a public product surface before proving that its data improves WatchSignal outcomes.

## Further Notes

The research brief lives in `docs/taste-lab-research-brief.md`.
The product backlog lives in `docs/product-backlog.md`.
Taste Lab should be treated as MVP plus 1 research infrastructure.
It changes the MVP plus 1 priority from "make recommendations better somehow" to "build a defensible taste-calibration loop and measure whether it improves recommendations."
