# Code-First MVP Issue Breakdown

This draft breaks [docs/prd-code-first-mvp.md](../prd-code-first-mvp.md) into GNHF-ready vertical slices.
It is not yet published to GitHub Issues.
Review granularity, dependencies, and HITL or AFK classification before publishing.

## Slice 1 - Local Dev Handshake

- Type: AFK
- Blocked by: None
- User stories covered: 3, 44, 45, 47

### What to build

Wire the existing Next.js shell to the FastAPI health endpoint and document one local command path for running both sides.
The goal is not product behavior yet.
The goal is to prove the local mobile web and backend can talk through the API boundary.

### Acceptance criteria

- [ ] The web app can call the API health endpoint and show a simple connected or disconnected state.
- [ ] The FastAPI `/health` endpoint remains covered by tests.
- [ ] The local run instructions explain how to open the web app from a phone on the same network.
- [ ] The validation commands pass.

### GNHF readiness

- Owned areas: `apps/web`, `apps/api/src/movie_night_mediator/api`, `README.md`
- Off-limits areas: scoring algorithm internals, TMDb integration, SQLite schema beyond what is needed for health
- Validation commands: `pnpm check`, web production build
- Stop condition: web shell visibly reports API health and all validation commands pass
- Learning artifact: short note or diagram showing browser to Next.js to FastAPI flow

## Slice 2 - SQLite Household Setup

- Type: AFK
- Blocked by: Slice 1
- User stories covered: 7, 8, 9, 12, 44, 45, 46, 47, 48

### What to build

Persist household setup and two configurable participant profiles in SQLite.
The committed defaults should be Husband and Wife.
The local app should be able to initialize or load this setup without committing real household data.

### Acceptance criteria

- [ ] SQLite database path is configurable through local environment settings.
- [ ] Household defaults can be created and loaded.
- [ ] Two participant profiles can be created and loaded.
- [ ] Real labels are not committed in fixtures or docs.
- [ ] Persistence tests prove setup survives a database round trip.

### GNHF readiness

- Owned areas: `apps/api/src/movie_night_mediator/storage`, `apps/api/src/movie_night_mediator/domain`, `apps/api/tests`
- Off-limits areas: `apps/web` except for minimal setup display if explicitly included, TMDb adapter, scoring weights
- Validation commands: `pnpm check`
- Stop condition: household setup persists to SQLite and tests pass
- Learning artifact: small schema diagram for household and participant profile tables

## Slice 3 - Setup Wizard For Profiles And Defaults

- Type: AFK
- Blocked by: Slice 2
- User stories covered: 3, 4, 5, 7, 8, 9, 42, 43

### What to build

Add the first mobile wizard path for reviewing or editing household profiles and defaults.
This should be polished enough to test on a phone, but not over-designed.
The wizard should call the backend setup endpoints rather than using hard-coded state.

### Acceptance criteria

- [ ] The web app shows setup state from the backend.
- [ ] The founder can keep generic defaults or update local profile labels.
- [ ] The setup screen is phone-friendly and pass-the-phone aware.
- [ ] A meaningful UI review artifact is produced if the design direction changes materially.
- [ ] The validation commands pass.

### GNHF readiness

- Owned areas: `apps/web`, setup-related API client code, setup route contracts
- Off-limits areas: recommendation scoring, TMDb search, Safe Pick gate
- Validation commands: web production build, `pnpm check`
- Stop condition: setup wizard reads and writes local setup through the API and builds successfully
- Learning artifact: compact screenshot or Lavish artifact for the setup flow if visually meaningful

## Slice 4 - Hybrid TMDb Title Resolution

- Type: AFK
- Blocked by: Slice 1
- User stories covered: 16, 17, 19, 49, 50

### What to build

Implement a TMDb adapter that searches for movie titles and returns likely matches.
Support storing resolved TMDb IDs and unresolved plain-text entries.
Keep tests deterministic through fakes or fixtures.

### Acceptance criteria

- [ ] The backend can search TMDb by title using local credentials.
- [ ] API behavior can return multiple candidate matches for a typed title.
- [ ] Resolved entries store TMDb ID and useful metadata.
- [ ] Unresolved entries can be saved without blocking the flow.
- [ ] Tests do not require live TMDb credentials.
- [ ] The live smoke test remains available for manual verification.

### GNHF readiness

- Owned areas: `apps/api/src/movie_night_mediator/adapters`, title-resolution domain models, title-resolution API tests
- Off-limits areas: mobile onboarding UI except for optional minimal API wiring, scoring, SQLite household setup except required persistence hooks
- Validation commands: `pnpm check`, optional `python3 scripts/tmdb_smoke_test.py` when credentials exist
- Stop condition: title resolution supports resolved and unresolved paths with deterministic tests
- Learning artifact: short note explaining live TMDb smoke tests versus deterministic adapter tests

## Slice 5 - Minimal Onboarding Seed Capture

- Type: AFK
- Blocked by: Slices 2 and 4
- User stories covered: 13, 14, 15, 16, 17, 32, 48, 49

### What to build

Let both participants provide seed titles and lightweight hard constraints.
The path should use hybrid title resolution and persist onboarding signals.
It may be plain and utilitarian, but it must unblock real recommendation input.

### Acceptance criteria

- [ ] Each participant can add Loved, Fine, and No seed titles.
- [ ] Seed titles can be stored as resolved TMDb items or unresolved text.
- [ ] Hard constraints such as horror exclusion and subtitle intolerance can be stored.
- [ ] Shared recommendation mode remains locked until required onboarding exists.
- [ ] Tests cover persistence and onboarding-completion behavior.

### GNHF readiness

- Owned areas: onboarding app service, onboarding API routes, onboarding persistence, related tests
- Off-limits areas: final recommendation UI, Safe Pick classification, scorer weight changes
- Validation commands: `pnpm check`, web production build if UI is touched
- Stop condition: both participant profiles can complete minimal onboarding and tests pass
- Learning artifact: brief flow diagram for setup to onboarding completion

## Slice 6 - Safe Pick Gate

- Type: AFK
- Blocked by: Slice 4
- User stories covered: 10, 11, 12, 20, 21, 22, 23, 34

### What to build

Classify candidate titles as Safe Pick, Needs Quick Check, or rejected.
The classifier should be honest about TMDb limitations and should not treat Amazon rent or buy as Prime subscription availability.
Manual verified-watchable corrections should be part of the model even if the UI for editing them stays minimal.

### Acceptance criteria

- [ ] Prime Germany provider classification distinguishes flatrate from rent and buy.
- [ ] Originally English titles can pass the language gate when provider availability passes.
- [ ] Foreign-language titles without verified English subtitles become Needs Quick Check.
- [ ] Already-watched titles are rejected unless rewatches are allowed.
- [ ] Manual verified-watchable corrections can upgrade or clarify watchability.
- [ ] Tests cover Safe Pick, Needs Quick Check, and rejected outcomes.

### GNHF readiness

- Owned areas: Safe Pick classifier, watchability domain models, classifier tests
- Off-limits areas: UI styling, TMDb live networking beyond fixture shape, scoring formulas except classifier inputs
- Validation commands: `pnpm check`
- Stop condition: classification behavior is fully covered by tests and no UI assumptions are required
- Learning artifact: decision table for Safe Pick versus Needs Quick Check

## Slice 7 - Mode-Aware Shared Scoring

- Type: AFK
- Blocked by: Slices 5 and 6
- User stories covered: 24, 25, 27, 33, 34, 35, 36, 41

### What to build

Extend the scoring core to rank Safe Pick candidates for a shared couple session.
The scorer should produce per-person scores, a session-mode-aware group score, concise reasons, and support one interesting Safe Pick when possible.

### Acceptance criteria

- [ ] Scorer accepts shared session context and two participant profiles.
- [ ] Husband-first, wife-first, and compromise modes produce observable ranking differences.
- [ ] Compromise protects against strong dislike.
- [ ] Main ranking uses Safe Picks only.
- [ ] One interesting Safe Pick can be included when available.
- [ ] Scoring tests verify observable ranking behavior rather than internal formula details.

### GNHF readiness

- Owned areas: scoring module, scoring contract tests, shared session domain models
- Off-limits areas: frontend wizard screens, live TMDb adapter, SQLite migration changes unless required by scorer inputs
- Validation commands: `pnpm check`
- Stop condition: mode-aware shared scoring passes tests for all session modes
- Learning artifact: scoring explanation note with inputs, outputs, and tunable weights

## Slice 8 - Shared Session API And State Machine

- Type: AFK
- Blocked by: Slices 2, 5, 6, and 7
- User stories covered: 4, 5, 24, 26, 27, 28, 29, 34, 35, 36, 44, 45, 46, 47

### What to build

Implement the pass-the-phone session state machine behind the API.
A session should move from start to founder reactions to handoff to wife reactions to reranked recommendation.
The API should expose workflow-friendly endpoints while preserving pragmatic REST resource shape.

### Acceptance criteria

- [ ] A shared session can be started after required onboarding exists.
- [ ] The active mode can be husband-first, wife-first, or compromise.
- [ ] Founder reactions are stored separately from wife reactions.
- [ ] The session enters a handoff state between reaction passes.
- [ ] The session reranks after both reaction passes are complete.
- [ ] State transition tests cover valid and invalid transitions.

### GNHF readiness

- Owned areas: session application service, session API routes, session persistence tests
- Off-limits areas: detailed mobile UI polish, TMDb adapter internals, unrelated onboarding refactors
- Validation commands: `pnpm check`
- Stop condition: API-driven pass-the-phone state machine works through reranking and tests pass
- Learning artifact: state-machine diagram

## Slice 9 - Mobile Pass-The-Phone Wizard

- Type: HITL
- Blocked by: Slices 3 and 8
- User stories covered: 3, 4, 5, 24, 26, 27, 28, 29, 42, 43

### What to build

Build the phone-first wizard screens for the shared recommendation flow.
The UI should guide the founder through starting a session, reacting to five titles, handing the phone over, collecting the second reaction pass, and viewing the recommended pick.

### Acceptance criteria

- [ ] The wizard clearly shows the current step and next action.
- [ ] The reaction screens use large, lightweight controls.
- [ ] The handoff screen is obvious and low-friction.
- [ ] The final screen shows best pick plus reranked shortlist.
- [ ] The UI is polished enough for couch testing.
- [ ] A Lavish or equivalent review artifact is produced before finalizing visual direction.
- [ ] Web production build passes.

### GNHF readiness

- Owned areas: `apps/web`, API client calls for session flow, lightweight UI docs
- Off-limits areas: backend scoring logic, Safe Pick classifier internals, database schema changes unless an API mismatch is found
- Validation commands: web production build, `pnpm check`
- Stop condition: wizard completes the happy path against the session API and the founder accepts the visual direction
- Learning artifact: Lavish artifact or compact screen-flow diagram

## Slice 10 - Outcome And Post-Watch Feedback

- Type: AFK
- Blocked by: Slice 8
- User stories covered: 30, 31, 32, 37, 38, 40

### What to build

Capture what actually happened after a recommendation and record per-person post-watch feedback.
Optional free-text notes should be stored but not interpreted by an LLM in MVP.

### Acceptance criteria

- [ ] A session can record watched recommended, watched other, or watched nothing.
- [ ] Per-person Loved, Fine, or No feedback can be stored.
- [ ] Optional free-text notes can be stored.
- [ ] Feedback updates watched history and session artifacts.
- [ ] Tests cover outcome and feedback persistence.

### GNHF readiness

- Owned areas: outcome and feedback services, persistence, API routes, tests
- Off-limits areas: LLM interpretation, recommendation scoring changes, UI polish beyond minimal wiring
- Validation commands: `pnpm check`
- Stop condition: outcomes and post-watch feedback persist correctly and tests pass
- Learning artifact: data-flow note from recommendation to feedback to history

## Slice 11 - Low-Polish Manual Backfill

- Type: AFK
- Blocked by: Slices 4 and 5
- User stories covered: 18, 23, 37, 38, 49

### What to build

Add a low-polish utility for adding watched-history backfill.
This does not need a beautiful couch UX.
It should support assigning entries to one participant or both, optional Loved, Fine, or No labels, and hybrid title resolution.

### Acceptance criteria

- [ ] Backfill entries can be added for one or both participants.
- [ ] Entries can be resolved through TMDb or saved unresolved.
- [ ] Optional Loved, Fine, or No labels are stored as useful taste signal.
- [ ] Backfill updates watched history.
- [ ] Tests cover resolved and unresolved backfill.

### GNHF readiness

- Owned areas: backfill API/service/persistence, minimal utility UI if included, tests
- Off-limits areas: main recommendation wizard polish, scoring formula changes, LLM interpretation
- Validation commands: `pnpm check`, web production build if UI is touched
- Stop condition: backfill can store useful watched-history signal and tests pass
- Learning artifact: short note explaining backfill's role versus onboarding seeds

## Slice 12 - History And Debug Visibility

- Type: AFK
- Blocked by: Slices 8 and 10
- User stories covered: 37, 38, 43, 50

### What to build

Add lightweight visibility into recent sessions, outcomes, reactions, and stored history.
This can be a simple local-only screen or API-backed debug view.
The goal is to support trust, learning, and agent debugging.

### Acceptance criteria

- [ ] Recent sessions can be listed.
- [ ] A session detail view shows shortlist, reactions, final pick, outcome, and feedback when present.
- [ ] The view does not expose secrets.
- [ ] The view uses generic committed examples only.
- [ ] Tests cover the API or service behavior behind the view.

### GNHF readiness

- Owned areas: history API/service, lightweight UI or debug route, tests, docs
- Off-limits areas: scoring formula changes, TMDb live call behavior, household setup changes
- Validation commands: `pnpm check`, web production build if UI is touched
- Stop condition: recent-session visibility works and validation passes
- Learning artifact: explanation of what is user-facing history versus internal debug artifact

## Slice 13 - First GNHF Trial Wrapper

- Type: HITL
- Blocked by: Slice 1
- User stories covered: 44, 45, 46, 47

### What to build

Run the first conservative GNHF trial on a tiny bounded task.
The preferred task is Slice 1 itself or a tiny subtask inside Slice 1, such as a small API contract enhancement with tests.
The goal is to validate the GNHF working method, not to accelerate product scope yet.
HITL means founder approval to launch the experiment and host-agent review afterward.
The founder does not need to babysit the run once it starts.

### Acceptance criteria

- [ ] The GNHF prompt includes objective, owned files, off-limits files, validation commands, and stop condition.
- [ ] The run happens in Companion mode.
- [ ] The host agent independently verifies the result.
- [ ] The result is either accepted, followed up with a bounded correction, or rejected with evidence.
- [ ] A short learning artifact records what worked and what to change before larger GNHF tasks.

### GNHF readiness

- Owned areas: one tiny backend endpoint and its tests, or another similarly narrow area
- Off-limits areas: broad product logic, UI redesign, database schema unless the trial explicitly targets it
- Validation commands: `pnpm check`
- Stop condition: the tiny task is complete, verified, and summarized without unrelated file changes
- Learning artifact: GNHF trial report
