# PRD - MVP Plus 3 Directed Discovery And Real Tester Profile

## Problem Statement

WatchSignal now has the core pass-the-phone flow, Taste Lab evidence, profile memory, steering, bookmarks, and continuation behavior from MVP Plus 2.
That makes the product feel more real, but it does not yet give the founder a durable personal test harness.
The next milestone should let the founder create a real tester profile, load actual taste data into it, steer new recommendation batches with normal language, and judge whether the product is improving.

The current risk is building more recommendation machinery without a dependable way to feel the payoff as a real user.
The founder needs a persistent profile named `Cezary - tester`, a calibration loop that survives reloads and restarts, and a directed discovery loop that can answer requests like "scary but not bleak", "sad but beautiful", or "something with Jack Nicholson in it".

MVP Plus 3 should prove this promise:

> I can create my own persistent tester profile, calibrate it with Taste Lab, then steer the next five picks with natural language and see recommendations adapt to my actual taste.

## Phase Status

MVP+3: [scoping: unknown total]

The issue count is not locked yet.
After the issue breakdown is accepted, new work should be classified as in-scope risk closure, a scope-change candidate that needs founder approval, or next-phase backlog.

## Solution

Build MVP Plus 3 as one phase named **Directed Discovery And Real Tester Profile**.
The phase should connect profile persistence, private calibration, directed candidate generation, continuation, saved titles, and evidence in one founder-dogfoodable loop.

The user-facing loop should become:

1. Create or select a persistent profile named `Cezary - tester`.
2. Rename the profile later without losing taste data.
3. Use that profile in Taste Lab.
4. Save Taste Lab ratings under that real profile identity.
5. Return to the main app with the same profile selected.
6. Generate an initial recommendation batch.
7. Add a natural-language nudge such as "scary but not bleak", "90s thriller", or "Jack Nicholson".
8. Confirm the interpreted filters and soft signals before applying them.
9. Ask for five more picks without seeing already-shown titles again.
10. Keep prior reactions, bookmarks, and active nudges visible enough to understand what changed.
11. Bookmark promising titles for later without treating the bookmark as an automatic taste vote.
12. See recommendation explanations that cite both durable profile evidence and tonight-level nudges.

Taste Lab should become part of the founder's private calibration loop, not a full public onboarding redesign.
The main app should support real saved profiles well enough for one named tester profile and one default partner profile.
The recommendation engine should remain inspectable.
LLM assistance may translate messy user language into structured filters and soft signals, but deterministic parsing should cover common cases and the scorer should keep final ranking authority.

## User Stories

1. As the founder, I want MVP Plus 3 to have a named phase boundary, so that ambitious discovery work does not sprawl.
2. As the founder, I want the current phase tracker to show scoping until issues are accepted, so that the count is not fake.
3. As the founder, I want a persistent `Cezary - tester` profile, so that I can load my real taste into the app.
4. As the founder, I want to rename that profile later, so that the test profile can become a normal profile without losing data.
5. As a household user, I want saved profiles to survive reloads and local app restarts, so that calibration work does not disappear.
6. As a household user, I want Taste Lab to ask which profile is rating, so that ratings belong to the right person.
7. As the founder, I want Taste Lab ratings to persist under the tester profile id, so that I can judge recommendation improvement over time.
8. As the founder, I want the main recommendation flow to use the selected real profile, so that Taste Lab work affects the product I am dogfooding.
9. As a household user, I want a second default or partner profile to stay available, so that the shared movie-night model remains intact.
10. As a household user, I want recommendation explanations to mention profile evidence when it matters, so that the app feels trustworthy.
11. As a household user, I want to ask for "five more" without losing prior reactions, so that a weak first batch does not force a restart.
12. As a household user, I want "five more" to exclude already-shown movies, so that the app does not waste attention.
13. As a household user, I want to add a new nudge before the next batch, so that I can steer toward what I actually want tonight.
14. As a household user, I want to say nudges in normal language, so that I do not need filter syntax.
15. As a household user, I want emotional requests like "scary", "sad", or "beautiful" to become visible signals, so that I understand how the app interpreted me.
16. As a household user, I want actor requests like "Jack Nicholson in it" to affect candidate generation, so that people-based discovery works.
17. As a household user, I want decade, mood, genre, runtime, provider, language, and rewatch constraints to become structured filters when possible, so that common requests behave predictably.
18. As a household user, I want the app to ask one short clarification when a request is ambiguous, so that "sad" can mean either matching or avoiding the mood.
19. As the founder, I want deterministic nudge parsing for common cases, so that required tests do not depend on live LLM calls.
20. As the founder, I want an LLM adapter path for fuzzier language, so that the product can become more natural without giving the LLM ranking authority.
21. As a household user, I want active nudges to remain visible and removable, so that I can understand and correct the direction.
22. As a household user, I want redo options such as same direction, different direction, more like this, avoid this, and add a new nudge, so that "five more" has useful intent.
23. As a household user, I want bookmarks to be real saved titles, so that promising movies survive the session.
24. As a household user, I want bookmarks to record who saved the title when known, so that saved interest has provenance.
25. As a household user, I want to remove a bookmark, so that the saved list stays useful.
26. As a household user, I want a bookmark to avoid becoming an automatic taste vote, so that curiosity does not pollute my profile.
27. As a household user, I want to use a bookmarked title as a future seed when practical, so that saved interest can help a later night.
28. As the founder, I want a phone-sized dogfood smoke to cover the tester profile, Taste Lab calibration, a directed nudge, five more, bookmark, and persistence, so that completion is grounded in the real flow.
29. As the founder, I want fixed recommendation scenarios to compare before and after profile calibration plus nudges, so that improvement is reviewable.
30. As the founder, I want famous-person taste matching kept as a stretch idea, so that MVP Plus 3 stays focused on the core product loop.
31. As an agent, I want each MVP Plus 3 issue to name owned behavior, blockers, validation, and stop condition, so that AFK work can proceed without drift.

## Implementation Decisions

- MVP Plus 3 is one phase named **Directed Discovery And Real Tester Profile**.
- The accepted MVP Plus 3 issue count is not locked until the founder approves the issue breakdown.
- The first implementation slice should define contracts and acceptance gates for profiles, Taste Lab ownership, nudges, redo semantics, bookmarks, and evidence.
- `Cezary - tester` is an intended real profile, not throwaway fixture copy.
- Profile identity must be stable by id even if the display name changes.
- The default household should still support two-person recommendation behavior.
- Taste Lab ratings belong to profile ids and should not silently merge people.
- Taste Lab becomes usable for founder calibration, but it does not become the main public onboarding flow in this phase.
- Main-flow recommendations should consume the selected profile's durable evidence.
- Tonight-level nudges are session context by default and should not rewrite durable profile taste.
- Common nudge categories should be deterministic first where practical.
- LLM interpretation may support fuzzier requests, but required validation should use deterministic fakes or fixtures.
- LLM output must become structured filters, soft signals, clarification prompts, and explanation text.
- LLMs do not own final ranking.
- Actor and person requests should use TMDb person metadata or a fixture-backed equivalent in tests.
- Five-more generation should preserve prior reactions, preserve or edit active nudges, and exclude already-shown movies.
- Redo flow should distinguish same direction, different direction, more like this, avoid this, and add nudge when the UI can support that distinction.
- Bookmarks are saved titles with provenance.
- Bookmarks are not automatic taste votes.
- Bookmark-as-seed is useful but can stay small in MVP Plus 3 if persistence and visibility are complete.
- Recommendation explanations should tell the user which durable profile evidence and tonight nudge affected a pick.
- The final acceptance gate should include both phone-sized dogfood proof and recommendation-quality proof.

## Testing Decisions

- Contract tests should cover profile identity, rename behavior, Taste Lab rating ownership, nudge interpretation, redo semantics, bookmark persistence, and recommendation evidence.
- Persistence tests should prove the tester profile and its Taste Lab ratings survive app reload or local restart boundaries.
- Taste Lab tests should prove ratings are stored and read by selected profile id.
- Candidate-generation tests should cover actor/person requests with committed fixtures rather than live network calls.
- Nudge tests should cover deterministic parsing for mood, genre, decade, runtime, language, provider, rewatch, and cast/person examples.
- UI or browser smoke should cover a phone-sized flow from profile selection through recommendation, nudge, five more, bookmark, and reload.
- Scoring tests should verify observable ranking or explanation changes when a calibrated profile and active nudge are present.
- Required validation should not depend on paid vendors, live LLM calls, or private user data.
- Production web build and beta preflight should pass before the phase is considered complete.

## Out of Scope

- Famous-person taste matching.
- Public celebrity taste profiles.
- Full taste archetype comparison.
- Full profile analytics dashboard.
- Full Taste Lab public redesign.
- Separate-device shared sessions.
- Account system or hosted authentication.
- Telegram adapter work.
- Paid vendor additions.
- Manual bulk watched-history import outside Taste Lab.
- LLM-owned ranking.
- Treating bookmarks as automatic likes.
- Publishing private founder taste data.

## Further Notes

Famous-person taste matching remains attractive because it could make taste identity playful and shareable.
It should be treated as a later prototype or MVP Plus 4 candidate after the real-profile calibration loop works.

The phrase "dogfood run" means using the app as a real user on a phone-sized flow and checking whether the experience actually holds together.
For MVP Plus 3, that means using `Cezary - tester`, entering real Taste Lab ratings, steering recommendations with natural language, asking for five more, bookmarking a title, reloading, and confirming the product remembers the right things.

The phase should feel ambitious because it connects data ownership, recommendation quality, and human steering into one loop.
It should still be bounded because the acceptance gate is one real tester profile, one shared recommendation flow, and visible evidence that calibration plus nudging changed results.
