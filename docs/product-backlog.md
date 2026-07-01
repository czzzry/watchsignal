# WatchSignal Product Backlog

This is the running list of product work that should not be forgotten while we focus on one MVP plus 1 slice at a time.
It is not a commitment to build everything next.
It is a parking lot for mature-product needs, rough edges, and future issue candidates.
GitHub issue publication remains a separate action that should only happen with explicit founder approval.

## Current MVP Plus 1 Focus

### Taste Lab: high-signal rapid rating

Goal: improve recommendation quality by collecting taste ratings from movies selected for high preference-information value.
The founder is willing to rate many movies if those movies are chosen intelligently.
The product question is whether WatchSignal can choose high-signal movies rather than asking for arbitrary ratings.

Questions to resolve:
- Does "high-signal movie" have a defensible statistical meaning?
- Can MovieLens-style ratings data identify movies with high preference-information value?
- What first signal-score formula should we use?
- How many high-signal ratings are needed before recommendations improve?
- How should `Haven't seen` be stored and deprioritized without treating it as dislike?

Candidate work:
- Taste Lab research brief.
- Taste Lab PRD and local issue breakdown.
- Offline signal-score script using MovieLens data.
- Private rapid-rating storage and API.
- Private Taste Lab route for batch-rating 10 movies at a time.
- Recommendation evaluation fixture for comparing high-signal rating against random or popularity-only rating.

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
- Add a manual watched-history backfill path that is fast enough to use casually.

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
