# MVP Plus 3 Issue Breakdown

This proposed issue set breaks [docs/prd-mvp-plus-3.md](../prd-mvp-plus-3.md) into bounded vertical slices.
It has been published to GitHub Issues as the locked MVP Plus 3 tracker.

## Current MVP Phase

MVP Plus 3 is **Directed Discovery And Real Tester Profile**.

Current tracker:

```text
MVP+3: [████████████████████] 10/10 issues done
```

The issue count is ten.
New work discovered during execution should be classified as in-scope risk closure, a scope-change candidate that needs founder approval, or next-phase backlog.

## Phase Promise

I can create my own persistent tester profile, calibrate it with Taste Lab, then steer the next five picks with natural language and see recommendations adapt to my actual taste.

The phase is done only when both are true:

- A phone-sized dogfood flow proves the tester profile, Taste Lab calibration, directed nudge, five-more generation, bookmark, and persistence path work together.
- A recommendation-quality report proves profile evidence and active nudges affect ranking or explanations in reviewable ways.

## Proposed GitHub Tracker

Parent PRD issue:

- #62 - MVP+3 PRD - Directed Discovery And Real Tester Profile

Implementation and acceptance slices:

- #63 - MVP+3 Slice 1 - Contracts And Acceptance Gate - done
- #64 - MVP+3 Slice 2 - Persistent Tester Profile Foundation - done
- #65 - MVP+3 Slice 3 - Taste Lab Profile Selection And Durable Ratings - done
- #66 - MVP+3 Slice 4 - Main Flow Uses Selected Profiles And Calibration Evidence - done
- #67 - MVP+3 Slice 5 - Directed Nudge Interpreter Contract - done
- #68 - MVP+3 Slice 6 - Actor And Person Candidate Filtering - done
- #69 - MVP+3 Slice 7 - Five More Redo Semantics And UI - done
- #70 - MVP+3 Slice 8 - Bookmark Library Lite - done
- #71 - MVP+3 Slice 9 - Recommendation Explanation Trust Polish - done
- #72 - MVP+3 Slice 10 - MVP Plus 3 Dogfood And Evaluation Gate - done

## Slice 1 - Contracts And Acceptance Gate

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: None
- User stories covered: 1, 2, 19, 20, 28, 29, 31
- Primary goal: lock the shared contracts for profile ownership, Taste Lab calibration, nudges, redo behavior, bookmarks, evidence, and acceptance.

### What to build

Define the MVP Plus 3 contract surface before implementation work fans out.
The contract should name the data and API expectations for persistent profiles, profile rename, Taste Lab rating ownership, selected recommendation profiles, nudge interpretation, actor/person filters, five-more redo semantics, bookmark provenance, and explanation evidence.
It should also define the final phone-sized dogfood path and recommendation-quality scenarios.

### Acceptance criteria

- [x] Profile contract uses stable ids and renameable display labels.
- [x] `Cezary - tester` is represented as a normal persistent profile, not special-case UI text.
- [x] Taste Lab rating ownership is defined by profile id.
- [x] Main recommendation session profile selection is explicit.
- [x] Nudge interpretation contract supports filters, soft signals, clarification, confidence, and deterministic fallback.
- [x] Actor/person requests are represented without giving the LLM ranking authority.
- [x] Five-more contract distinguishes same direction, different direction, more like this, avoid this, and add nudge.
- [x] Bookmark contract stores source movie identity, provenance, remove behavior, and no automatic taste boost.
- [x] Evidence contract can explain durable profile signals and tonight-level nudges separately.
- [x] Acceptance gate contract names the phone-sized dogfood flow and fixed recommendation scenarios.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when later slices can build against shared contracts without inventing incompatible payloads.

Completed by the executable contract module in `apps/api/src/movie_night_mediator/mvp_plus_3/contracts.py` and contract tests in `apps/api/tests/test_mvp_plus_3_contracts.py`.
Treehouse fanout can now start with Slices 2, 3, 5, and 8.

### Risk notes

Keep this slice thin.
Do not implement the whole feature set inside the contract slice.

## Slice 2 - Persistent Tester Profile Foundation

- Type: AFK with HITL review if the profile UI changes materially
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 1
- User stories covered: 3, 4, 5, 9
- Primary goal: make `Cezary - tester` a durable, renameable profile that survives local use.

### What to build

Add the minimum real profile management needed for the founder dogfood loop.
The app should support creating or selecting `Cezary - tester`, renaming the display label later, and keeping one default or partner profile available for shared recommendation behavior.
Persistence should be profile-id based so renames do not orphan taste data.

### Acceptance criteria

- [x] The user can create or select a `Cezary - tester` profile.
- [x] The profile has a stable id separate from the display label.
- [x] The profile can be renamed without losing stored identity.
- [x] The profile persists through reload or local app restart boundaries.
- [x] A second default or partner profile remains available for the shared flow.
- [x] Tests cover create, select, rename, and reload behavior.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

### Stop condition

Stop when a real tester profile can be selected repeatedly without relying on reset fixtures.

Completed by setup store operations and API routes for ensuring the tester profile and renaming profiles.
The Next.js API proxy exposes the same operations to the web app.

### Risk notes

Avoid a full account system.
This is local persistent profile management, not hosted identity.

## Slice 3 - Taste Lab Profile Selection And Durable Ratings

- Type: AFK with HITL visual review if Taste Lab flow changes materially
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 2
- User stories covered: 6, 7, 8
- Primary goal: let the tester profile build real Taste Lab evidence.

### What to build

Update Taste Lab so ratings are tied to the selected real profile.
The founder should be able to select `Cezary - tester`, rate Taste Lab candidates, reload, and see those ratings remain attached to that profile.
Existing Taste Lab evidence read models should continue feeding WatchSignal profile evidence.

### Acceptance criteria

- [x] Taste Lab shows the selected rating profile.
- [x] The user can choose `Cezary - tester` for Taste Lab rating.
- [x] Saved ratings include the tester profile id.
- [x] Ratings survive reload or local restart boundaries.
- [x] The profile evidence read model can read the tester profile's Taste Lab ratings.
- [x] Tests prove ratings remain profile-specific.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

### Stop condition

Stop when Taste Lab can be used as the founder's real private calibration path.

Completed by dynamic Taste Lab profile loading through the setup profile API and a backend regression proving `Cezary - tester` owns durable Taste Lab ratings.

### Risk notes

Do not turn Taste Lab into the full public onboarding experience.

## Slice 4 - Main Flow Uses Selected Profiles And Calibration Evidence

- Type: AFK with phone-sized UX smoke
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 2, Slice 3
- User stories covered: 8, 9, 10, 29
- Primary goal: make the couch-flow recommendations actually consume selected real profile evidence.

### What to build

Connect the selected tester profile to the main recommendation flow.
Recommendations should use the tester profile's durable evidence where available while preserving the two-person movie-night model.
The result screen or evidence surface should show when Taste Lab or durable profile signals influenced a pick.

### Acceptance criteria

- [x] The main flow can start with `Cezary - tester` selected.
- [x] A second profile can participate in the shared recommendation flow.
- [x] Tester profile Taste Lab evidence is available to scoring.
- [x] Recommendation explanations mention profile evidence when it materially affects a result.
- [x] Tests prove profile evidence is not collapsed across people.
- [ ] Phone-sized smoke covers selected profiles through a recommendation result.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

```sh
pnpm beta:dogfood
```

### Stop condition

Stop when calibration work can visibly influence the main flow for the selected tester profile.

Completed by promoting the tester profile into the first main-flow slot, keeping the partner profile available, loading Taste Lab profile summaries into the result view, and preserving per-profile Taste Lab evidence in scoring.
The remaining phone-sized proof belongs to the final MVP Plus 3 dogfood gate.

### Risk notes

Avoid hiding the profile connection in debug-only output.
The founder needs enough visible evidence to judge whether calibration is helping.

## Slice 5 - Directed Nudge Interpreter Contract

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 1
- User stories covered: 13, 14, 15, 17, 18, 19, 20, 21
- Primary goal: turn normal-language direction into structured, confirmable recommendation context.

### What to build

Implement or extend the nudge interpreter for common directed-discovery requests.
Deterministic parsing should cover common categories such as mood, genre, decade, runtime, language, provider, rewatch, and cast/person terms where practical.
LLM-backed interpretation can remain an adapter path, but the required validation should use deterministic behavior or fakes.

### Acceptance criteria

- [x] "scary but not bleak" produces visible mood and tone signals.
- [x] "sad but beautiful" produces visible emotional signals and asks clarification if needed.
- [x] "90s thriller" produces decade and genre filters.
- [x] "nothing with subtitles tonight" produces a language or subtitle-related constraint.
- [x] "Jack Nicholson in it" produces a person/cast intent for the candidate layer.
- [x] Active nudges are visible, confirmable, and removable.
- [x] Tests cover deterministic parsing and clarification behavior.
- [x] LLM output, if used, is constrained to the same contract.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when user language becomes structured context that later slices can apply to candidate generation and scoring.

Completed by deterministic directed nudge interpretation in `apps/api/src/movie_night_mediator/app/tonight_intent.py`.
The interpreter emits MVP Plus 3 `DirectedNudge` objects for active nudges while preserving the existing tonight intent path.

### Risk notes

Do not let the LLM pick winners.
The interpreter should produce inputs that the code-owned recommender can inspect.

## Slice 6 - Actor And Person Candidate Filtering

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 5
- User stories covered: 16, 17, 20
- Primary goal: make people-based discovery real enough for requests like "Jack Nicholson in it".

### What to build

Extend candidate generation so actor or person nudges can affect the candidate pool.
Use TMDb person metadata in the live path and committed fixtures in required tests.
The result should support actor requests without requiring the LLM to rank movies.

### Acceptance criteria

- [x] Person-name intent can be resolved into candidate-generation constraints.
- [x] Live provider behavior uses TMDb person or credits metadata where available.
- [x] Required tests use fixtures and do not need network access.
- [x] Candidate results exclude already-shown titles where session continuation requires it.
- [x] Explanations can mention the person nudge when it influenced a result.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when the app can generate a meaningful next batch for a named actor request.

Completed by person candidate constraints on session context, fixture actor filtering, matched person metadata, and a TMDb person search plus credits hook with fake-client tests.

### Risk notes

Do not broaden this into a full cast, crew, and filmography browser.

## Slice 7 - Five More Redo Semantics And UI

- Type: AFK with phone-sized UX smoke
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 4, Slice 5
- User stories covered: 11, 12, 13, 21, 22
- Primary goal: make "five more" feel like directed continuation rather than restart.

### What to build

Build the redo flow around explicit next-batch intent.
The user should be able to ask for the same direction, a different direction, more like this, avoid this, or add a new nudge.
The app should preserve prior reactions, preserve or edit active nudges, exclude already-shown titles, and keep enough context visible to feel trustworthy.

### Acceptance criteria

- [x] Five-more generation keeps prior reactions active.
- [x] Five-more generation excludes already-shown titles.
- [x] The user can continue with the same active direction.
- [x] The user can add a new nudge before generating the next batch.
- [x] The user can remove or replace an active nudge.
- [x] "More like this" and "avoid this" behavior is represented in session context when supported by the UI.
- [ ] Phone-sized smoke covers first batch, nudge, five more, and no repeated titles.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

```sh
pnpm beta:dogfood
```

### Stop condition

Stop when redo creates a useful next batch without erasing the current session.

Completed by preserving active intents and session reactions through continuation, excluding already-shown titles in shortlist requests, and adding quick redo prompts for different direction, more like the winner, and avoiding the winner.
The remaining phone-sized proof belongs to the final MVP Plus 3 dogfood gate.

### Risk notes

Keep the UI compact.
This should feel like a couch-control flow, not an advanced search panel.

## Slice 8 - Bookmark Library Lite

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 2
- User stories covered: 23, 24, 25, 26, 27
- Primary goal: make saved titles persist and remain inspectable without becoming a full library product.

### What to build

Finish the bookmark feature as a small saved-title library.
The user should be able to bookmark a recommended title, see it later, know who saved it when known, remove it, and optionally use it as a future seed if the current recommender path can support that cleanly.

### Acceptance criteria

- [x] A recommended title can be bookmarked.
- [x] Bookmarks persist through reload or local restart boundaries.
- [x] Bookmarks show who saved the title when the active profile is known.
- [x] A bookmark can be removed.
- [x] Bookmarking does not count as an automatic like or taste rating.
- [x] Bookmark-as-seed is either implemented in a small way or explicitly deferred in the acceptance note.
- [x] Tests cover persistence, remove behavior, and no automatic taste boost.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

### Stop condition

Stop when bookmarks are trustworthy saved titles, not decorative buttons.

Completed by durable watchlist bookmark metadata, saved-by display labels, duplicate-save provenance preservation, remove behavior, migration coverage, and explicit non-seed/non-taste-signal payloads.

### Risk notes

Do not build a full streaming queue, review shelf, or public library system.

## Slice 9 - Recommendation Explanation Trust Polish

- Type: AFK with HITL review if explanation UI changes materially
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 4, Slice 5, Slice 7, Slice 8
- User stories covered: 10, 15, 21, 29
- Primary goal: make the app explain what changed because of profile calibration and tonight-level nudges.

### What to build

Polish the result and evidence surfaces so users can see why a pick appeared.
Explanations should distinguish durable profile evidence, Taste Lab-derived evidence, active nudges, session reactions, bookmarks when relevant, and fallback behavior.
This should be user-facing enough for dogfood judgment without exposing raw debug clutter.

### Acceptance criteria

- [x] A recommendation can mention durable profile evidence when used.
- [x] A recommendation can mention an active nudge when used.
- [x] Explanations distinguish durable taste from tonight context.
- [x] Fallback behavior remains honest when evidence is weak.
- [x] The result view remains phone-first and does not become crowded.
- [x] Tests cover explanation payloads for profile evidence and active nudges.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

### Stop condition

Stop when the founder can tell why the recommendation changed without opening developer tools.

Completed by adding a compact result evidence panel for active nudges, Taste Lab signal counts, and matched person names, plus shortlist payload support for person matches.

### Risk notes

Avoid overpromising precision.
Explanations should be useful, not magical.

## Slice 10 - MVP Plus 3 Dogfood And Evaluation Gate

- Type: AFK with HITL final review
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 2, Slice 3, Slice 4, Slice 5, Slice 6, Slice 7, Slice 8, Slice 9
- User stories covered: 1, 2, 28, 29, 31
- Primary goal: prove MVP Plus 3 is done with real-flow and recommendation-quality evidence.

### What to build

Create the founder-facing acceptance gate for MVP Plus 3.
The gate should include a phone-sized dogfood run, persistence proof, and fixed recommendation-quality scenarios.
It should say whether the phase is complete and should not quietly add new scope.

### Acceptance criteria

- [x] The acceptance note records the current phase and accepted issue count.
- [x] The dogfood flow uses `Cezary - tester` or a local-safe equivalent that proves the same profile behavior.
- [x] The dogfood flow covers Taste Lab rating, main-flow recommendation, directed nudge, five more, bookmark, reload, and persistence.
- [x] The recommendation-quality report compares profile calibration plus nudges against a baseline.
- [x] The report shows rank changes, top-pick changes, explanation excerpts, and visible caveats.
- [x] Beta preflight, production web build, and phone-sized smoke pass.
- [x] The acceptance note states whether MVP Plus 3 is complete.

### Validation commands

```sh
pnpm beta:preflight
```

```sh
pnpm build:web
```

```sh
pnpm beta:dogfood
```

### Stop condition

Stop when MVP Plus 3 has both product-flow proof and recommendation-quality proof.

Completed by the accepted MVP Plus 3 gate in `docs/validation/mvp-plus-3-acceptance-gate-2026-07-07.md`.

### Risk notes

Do not use private real taste data in committed fixtures or public artifacts.
If real founder data is used locally, summarize the result without publishing the private details.

## Scope Candidates Not Pulled Into MVP Plus 3

- Famous-person taste matching.
- Taste archetype quizzes.
- Public taste profiles.
- Full profile analytics dashboard.
- Full Taste Lab public onboarding redesign.
- Separate-device live household sessions.
- Hosted accounts and auth.
- Telegram adapter.

These remain strong future candidates after the real-profile calibration and directed discovery loop is working.
