# WatchSignal Product Backlog

This is the running list of product work that should not be forgotten while we focus on one MVP plus 1 slice at a time.
It is not a commitment to build everything next.
It is a parking lot for mature-product needs, rough edges, and future issue candidates.
GitHub issue publication remains a separate action that should only happen with explicit founder approval.

## Current MVP Plus 2 Focus

### Memory, Steering, And Rich Recommendation Intelligence

Goal: prove that WatchSignal has memory and taste steering, not just a one-night flow.
MVP plus 1 proved that Taste Lab ratings can update WatchSignal taste evidence.
MVP plus 2 should make the main product feel materially more mature by combining profile identity, shared watchlist memory, Show 5 more, Steer next 5, LLM intent interpretation, and richer recommendation intelligence.

Taste Lab should remain private and optional for now.
The main app should benefit from its saved signals without making Taste Lab part of the normal couch-flow UI.
The main app should not add a competing manual backfill flow because Taste Lab remains the future intentional calibration and bulk-rating service.

Questions to resolve:
- What contract lets Treehouse workers parallelize profile memory, watchlist, intent, continuation, enrichment, scoring, and evaluation?
- What is the smallest profile identity setup that makes saved and rated signals feel owned by real people?
- How should a shared household watchlist work without becoming an automatic taste vote?
- How should natural-language tonight intent become structured filters and soft signals without giving the LLM ranking authority?
- How should Show 5 more and Steer next 5 preserve prior reactions and filters?
- How much MovieLens Tag Genome or offline feature enrichment can be used safely in MVP plus 2?
- What recommendation-quality report proves that richer profile and enrichment evidence improved ranking behavior?

Candidate work:
- MVP plus 2 PRD and issue breakdown.
- MVP plus 2 architecture and data contracts.
- Profile labels and lightweight avatars.
- Shared household watchlist with remove.
- App-owned watched and rating actions.
- Small profile memory panel.
- Tonight intent interpreter with confirm-before-apply and clarification behavior.
- Show 5 more and Steer next 5.
- Hybrid TMDb plus MovieLens Tag Genome or offline feature enrichment.
- Rich recommendation scoring and evidence.
- MVP plus 2 evaluation and acceptance gate.

## Mature Product Backlog

### Recommendation Quality

- Improve candidate generation beyond popularity plus simple filters.
- Use stored reactions, post-watch feedback, and watched-history backfill as learning signals.
- Separate durable taste learning from tonight-specific mood or constraints.
- Add a recommendation evaluation harness so scoring changes can be compared against fixed scenarios.
- Keep explanations honest when the model is uncertain.
- Decide when LLM-assisted interpretation should enter the learning loop.

### Taste Data And Onboarding

- Make it easier to add taste data.
- Show how many taste entries are required before the user can continue.
- Show completed count and remaining count in the taste entry UI.
- Explore faster title search, suggested seed lists, bulk entry, and lighter guided prompts.
- Improve the onboarding-required screen if it becomes demo-facing or public-facing.
- Add mature profile selection where each person can enter a name and choose from available avatars.
- For the full product, consider letting users take a photo or select an existing phone photo as their profile image.
- Add a manual watched-history backfill path that is fast enough to use casually.

### Taste Lab UX Stabilization

- Fix movie poster loading in the private Taste Lab flow.
- Make the initial action clear so users do not need to press refresh after seeding the demo queue.
- Rename or reposition `Save batch` so it reads like a confirmation action at the end of a rating batch.
- Keep confirmation controls near the bottom of the rating flow, where users expect them after reviewing the cards.
- Explain whether actions were saved and what will happen after saving.
- Keep `Haven't seen` as familiarity only, not a taste vote.
- Remove `Haven't seen` items from the rapid-rating queue after confirmation so users are not asked about the same movie again.
- Make refresh behavior understandable when no unrated candidates remain.
- Support the intended loop from the bottom of the page: generate 10 movies, rate them, confirm the batch, then generate the next 10 without scrolling back to the top.
- Ensure each new generated batch excludes movies already answered, including movies marked `Haven't seen`.
- Replace the fallback message `Session API is not reachable at http://127.0.0.1:8000. Using the local demo flow.` with clearer user-facing recovery copy.
- Add a better empty or stalled state when the queue cannot refresh from the API.
- Treat the current private Taste Lab UI as functionally useful but not mature-product quality.

### Result Actions And Library

- Make the save-to-library or add-to-watchlist button real, or hide it until it is real.
- Define what a saved title means.
- Decide whether saved titles are a watchlist, a library, a shortlist memory, or a future learning signal.
- Show clear feedback after saving so the user knows what happened.
- Add a way to view saved titles later.

### Restart And Session Safety

- Make restart harder to trigger by accident.
- Explain what happens to the current session when restart is pressed.
- Decide whether restart discards reactions, saves an abandoned session, or starts a new session while preserving history.
- Consider a confirmation step when restart would discard useful data.
- Add a gentler refine-search path when the shortlist is weak so restart is not the only escape hatch.

### Session History And Learning Loop

- Make recent sessions easy to inspect.
- Show what was recommended, what was chosen, and what feedback was captured.
- Preserve enough recommendation evidence to debug why a pick happened.
- Ask what happened after the movie if feedback was skipped.
- Track whether shortlist usage, restarts, and feedback trends improve over time.

### UX Polish

- Bring onboarding and setup up to the same visual quality as the pass-the-phone flow.
- Continue aligning the main app with the locked north-star direction.
- Keep phone-first interaction safe for couch use.
- Avoid demo or showcase screens that look cheaper than the real app.
- Keep real poster art in public and portfolio-facing materials.

### Public Portfolio And Marketability

- Keep the repo public and recruiter-readable.
- Keep the README oriented around product judgment, architecture, and visible demo value.
- Add a README section on research-backed Taste Lab calibration with citations to the specific cold-start, value-of-information, MovieLens, and item-discrimination sources used.
- Improve the recruiter demo later so it shows the Taste Lab calibration loop, not only the final couch-flow result.
- Maintain a short showcase/demo path for recruiters.
- Avoid publishing private household data, real secrets, or overly personal context.
- Consider a concise technical case-study page once the product story stabilizes.

## Not Now

- Do not publish local backlog items as GitHub issues without explicit founder approval.
- Do not add paid vendors without founder approval.
- Do not turn MVP plus 1 into a broad mature-product rebuild.
- Do not redesign every screen before improving the core recommendation loop.
