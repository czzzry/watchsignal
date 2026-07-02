# PRD - MVP Plus 2 Memory, Steering, And Rich Recommendation Intelligence

## Problem Statement

WatchSignal can now run a local shared movie-night flow and can use private Taste Lab ratings as profile evidence.
That proves the app can collect signals and route them into recommendation behavior.
It does not yet prove that WatchSignal feels like a product with memory.
It also does not yet prove that the recommendation engine can use rich movie-level evidence beyond genre counts.

The current risk is phase drift.
The next milestone must be large enough to feel like a real product jump, but bounded enough that everyone can tell when it is done.
The founder needs a clear current-phase tracker, a locked issue count after slicing, and a done proof that combines user-visible behavior with recommendation-quality evidence.

MVP Plus 2 should prove that WatchSignal has memory and taste steering, not just a one-night flow.
The user should be able to create recognizable profiles, save likely future watches, rate or mark watched titles that already appear in the app, ask for five more without losing signal, steer the next five with natural language, and see that richer recommendation evidence changed ranking behavior.

## Solution

Build MVP Plus 2 as one phase named **Memory, Steering, And Rich Recommendation Intelligence**.
The phase should not be split into MVP Plus 2A and MVP Plus 2B.
Instead, it should use internal milestones and vertical issues that can be parallelized through Treehouse-style work once the contracts are clear.

The user-facing loop should become:

1. Set up two lightweight profiles with labels and avatars.
2. Enter a tonight-level natural-language intent when useful.
3. Confirm the app's interpretation before it affects candidate generation.
4. Rate five movies in the shared flow.
5. Save likely future watches to a shared household watchlist.
6. Mark app-owned titles as watched or rate them when relevant.
7. Ask for **Show 5 more** without losing prior ratings.
8. Ask for **Steer next 5** to add another natural-language filter before generating the next batch.
9. Inspect a small profile memory panel that shows enough signal to prove the app remembers.
10. See recommendation explanations and evaluation output that show richer evidence was used.

The recommendation engine should become richer without becoming opaque.
TMDb remains the live candidate and display source.
MovieLens Tag Genome or derived offline features should enrich candidates where a reliable mapping exists.
LLM interpretation should translate messy human intent into structured filters and soft signals, but should not rank movies directly.
The scorer should remain code-owned and inspectable.
Fallback candidates without rich enrichment are allowed, but the app and evaluation report must track enrichment coverage.

Taste Lab stays out of the visible main app flow for MVP Plus 2.
Its backend profile-evidence path remains available.
Taste Lab is the future intentional calibration and manual rating service, so MVP Plus 2 should not add a competing standalone manual backfill flow.

## User Stories

1. As the founder, I want MVP Plus 2 to have a named phase boundary, so that the work cannot silently grow forever.
2. As the founder, I want an x/y issue tracker for the current MVP phase, so that I know when the phase is done.
3. As the founder, I want the issue count locked after PRD-to-issues, so that new discoveries become approved scope changes or future backlog.
4. As a household user, I want to rename the two profiles, so that the app feels like it belongs to real people.
5. As a household user, I want lightweight avatars or profile colors, so that I can recognize whose turn or signal I am seeing.
6. As a household user, I want profile identity to appear consistently in the pass-the-phone flow, so that I do not confuse one person's reactions with the other's.
7. As a household user, I want profile identity to appear in saved items and memory summaries where relevant, so that saved and rated signals have clear ownership.
8. As a household user, I want a shared household watchlist, so that we can keep likely future movies in one place.
9. As a household user, I want to save a movie for later from the app, so that a promising title does not disappear after tonight.
10. As a household user, I want to remove a saved movie, so that the watchlist stays useful.
11. As a household user, I want saves to be shared by default during a shared watch flow, so that the list matches the movie-night use case.
12. As a household user, I want the app to record who saved a movie when known, so that later profile-specific behavior remains possible.
13. As a household user, I want saving a movie to avoid becoming an automatic taste vote, so that curiosity does not pollute my taste profile.
14. As a household user, I want to mark a recommended, saved, or historical movie as watched, so that the app can remember what happened.
15. As a household user, I want to rate an app-owned watched movie with a simple label, so that the app can learn from real use.
16. As a household user, I want no separate manual backfill flow in the main app, so that WatchSignal does not duplicate Taste Lab.
17. As the founder, I want Taste Lab to remain outside the visible main app flow for now, so that the couch flow stays focused.
18. As the founder, I want the backend Taste Lab-to-profile connection to remain usable, so that private calibration can still affect WatchSignal evidence.
19. As a household user, I want a small profile memory panel, so that I can see that the app remembers useful signals.
20. As a household user, I want the memory panel to show saved count, recent reactions, watched/rated count, and simple taste signals, so that it is useful without becoming a dashboard.
21. As the founder, I want a full taste profile dashboard kept for future scope, so that MVP Plus 2 does not become an analytics project.
22. As a household user, I want to say tonight-level intent in normal language, so that I do not need to know filter syntax.
23. As a household user, I want examples like "I feel like laughing tonight" to become tonight-specific intent, so that the app adapts to mood without rewriting my profile.
24. As a household user, I want examples like "something from the 90s" to become structured filters, so that the app can actually use what I said.
25. As a household user, I want examples like "a Mel Gibson movie I haven't seen" to become structured person and rewatch filters, so that the request affects candidate generation.
26. As a household user, I want ambiguous emotional statements to trigger one short clarification, so that "I feel sad" does not automatically mean "show sad movies."
27. As a household user, I want the app to confirm its interpretation before applying it, so that I can catch misunderstandings.
28. As the founder, I want LLM output constrained to a structured intent contract, so that the product behavior is testable.
29. As the founder, I want deterministic fallback behavior for tests and local development, so that the app does not depend on live LLM calls for every validation run.
30. As the founder, I want no LLM ranking authority, so that recommendations stay inspectable.
31. As a household user, I want **Show 5 more** instead of **Start over**, so that I do not lose the movies I just rated.
32. As a household user, I want **Show 5 more** to exclude movies already shown, so that I do not waste time on repeats.
33. As a household user, I want **Show 5 more** to keep prior reactions active, so that the next batch learns from the current session.
34. As a household user, I want **Steer next 5**, so that I can refine the direction after the first batch teaches me what I actually want.
35. As a household user, I want steering to be additive within tonight, so that "funny" plus "set in New York" plus "set in fall" can shape later batches.
36. As a household user, I want the app to keep prior steering filters visible, so that I understand what is influencing the next batch.
37. As the founder, I want TMDb to remain the live candidate and display source, so that posters, public metadata, and provider-aware candidate generation stay practical.
38. As the founder, I want MovieLens Tag Genome or offline feature data used where available, so that the scorer can use dimensions richer than TMDb genres.
39. As the founder, I want candidates without rich enrichment to fall back gracefully, so that the app is not brittle when mapping coverage is incomplete.
40. As the founder, I want enrichment coverage tracked visibly, so that I can tell whether the richer recommender is really being used.
41. As a household user, I want recommendations to use movie-level evidence, so that rating 200 movies does not collapse into only genre counts.
42. As a household user, I want recommendations to use title similarity and richer taste dimensions, so that "similar to movies you liked" becomes real behavior.
43. As a household user, I want recommendation explanations to identify which signals moved a pick, so that the app feels trustworthy.
44. As the founder, I want a fixed evaluation report, so that recommendation changes are judged against repeatable scenarios.
45. As the founder, I want the evaluation report to compare baseline, fallback, and enriched scoring, so that we know what improved.
46. As the founder, I want the evaluation report to show rank deltas, top-pick changes, explanation excerpts, and enrichment coverage, so that the result is reviewable.
47. As the founder, I want MVP Plus 2 to require phone-sized click-through proof, so that user-flow quality is validated.
48. As the founder, I want MVP Plus 2 to require recommendation-quality proof, so that the phase does not end with UI-only progress.
49. As an agent, I want architecture and data contracts locked before parallel implementation, so that Treehouse workers can avoid incompatible assumptions.
50. As an agent, I want each issue to name owned behavior, blockers, validation, and stop condition, so that bounded work can proceed without drift.

## Implementation Decisions

- MVP Plus 2 is one phase named **Memory, Steering, And Rich Recommendation Intelligence**.
- The current phase tracker should show only the current MVP phase unless historical status is explicitly requested.
- After issue slicing is accepted, the x/y issue count is locked unless the founder approves a scope change.
- The first implementation slice should define architecture and data contracts for parallel work.
- Profile setup includes labels and lightweight avatars.
- Profile setup does not include photo upload.
- Profile setup does not become a full onboarding redesign.
- Taste Lab remains out of the visible main app flow.
- Taste Lab backend evidence remains available to WatchSignal profile evidence.
- Manual backfill does not become a separate main-app flow.
- Taste Lab remains the future intentional manual rating and calibration service.
- Main-app watched and rating actions apply only to movies already present in recommendation results, session history, or the saved list.
- Save for later means a shared household watchlist entry.
- Saved movies are removable.
- Saved movies do not automatically boost recommendation scoring in MVP Plus 2.
- Watchlist entries should support `saved_by_profile_id` when known.
- The visible watchlist is shared by default.
- A small profile memory panel is in scope.
- A full taste profile dashboard is future scope.
- Natural-language intent is tonight-level by default, not permanent profile editing.
- LLM interpretation must produce structured intent that the app can confirm before applying.
- Ambiguous emotional intent should ask one short clarification before candidate generation.
- Concrete intent can go directly to confirm-before-apply.
- Deterministic fallback behavior is required for tests and local development.
- LLMs may interpret human language, but the scoring module owns final ranking.
- **Show 5 more** replaces **Start over** as the primary continuation action.
- **Show 5 more** preserves current session reactions and avoids already-shown candidates.
- **Steer next 5** applies an additional confirmed tonight-level intent before generating another batch.
- Tonight-level steering accumulates within the session unless the user explicitly removes or replaces a steer.
- TMDb remains the live candidate and display source.
- MovieLens Tag Genome or derived offline features enrich scoring where candidate mapping exists.
- Fallback scoring remains available for candidates without enrichment.
- Enrichment coverage must be visible in evaluation output and debug or evidence surfaces.
- Recommendation scoring should use movie-level profile evidence, title similarity, richer feature dimensions, and existing hard constraints.
- Scoring explanations should distinguish genre evidence, title similarity, feature/tag evidence, tonight intent, session reactions, and fallback behavior where practical.
- Recommendation snapshots or evidence views should store enough information to review how enriched scoring affected a pick.
- MVP Plus 2 is done only when both user-flow proof and recommendation-quality proof exist.

## Testing Decisions

- Tests should validate external behavior and data contracts rather than exact private weight choices.
- Contract tests should cover intent interpretation payloads, clarification behavior, watchlist entries, profile identity, profile memory summaries, session continuation, and enrichment coverage.
- API or service tests should prove saved watchlist items can be added, listed, and removed.
- API or service tests should prove app-owned movies can be marked watched or rated without introducing a separate manual backfill flow.
- UI tests or phone-sized browser click-through should cover profile setup, natural-language intent confirmation, shared flow, Show 5 more, Steer next 5, saving, removing, and memory visibility.
- LLM tests should use deterministic fakes and should not require live network calls.
- Live LLM smoke tests may be optional and should be documented separately from required validation.
- Enrichment tests should use committed fixtures and should not require downloaded MovieLens datasets.
- Scoring tests should verify observable ranking changes, explanations, and fallback behavior.
- Evaluation tests should compare baseline, fallback, and enriched scoring across fixed scenarios.
- Production web build and full repo checks are required for UI-facing completion.
- The final acceptance gate should include a phone-sized click-through and a regenerated recommendation-quality report.

## Out of Scope

- Public product launch.
- Hosted deployment.
- Separate-phone shared sessions.
- Full account or authentication system.
- Photo upload for profiles.
- Full taste profile dashboard.
- Making Taste Lab visible as part of the normal app flow.
- A separate manual watched-history backfill flow.
- Treating saved-for-later as an automatic taste vote.
- LLM ranking authority.
- Black-box recommender decisions that cannot be inspected.
- Requiring every TMDb candidate to map perfectly to MovieLens or Tag Genome data.
- Committing downloaded MovieLens datasets or generated proprietary artifacts.
- Paid vendors beyond already-approved local credentials and explicit future approval.
- Tag Genome or enrichment claims without license and artifact handling notes.

## Further Notes

The phase emerged from a grill session after MVP Plus 1 was completed.
MVP Plus 1 proved that Taste Lab ratings can update WatchSignal taste evidence.
MVP Plus 2 should prove that WatchSignal remembers, can be steered in human language, and can use richer movie evidence than genres alone.

The current product slogan for the phase is:

> WatchSignal has memory and taste steering, not just a one-night flow.

The future full profile dashboard should include inferred preferences, Taste Lab evidence, similarity anchors, history, confidence, and "why we think this."
That dashboard is intentionally not part of MVP Plus 2.

The issue breakdown should preserve parallelization lanes for contracts, profile and memory UI, watchlist and session continuation, LLM intent, enrichment, scoring, and evaluation.
