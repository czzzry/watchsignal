# PRD - MVP+7 Refactor Stabilization

## Problem Statement

The app now has working MVP+6 behavior on `main`, but several high-change areas are accumulating structural risk.
The founder can keep shipping features, but each new change now costs more confidence because key contracts, route wiring, live-candidate fetching, and pass-the-phone state are harder to reason about than they should be.
The problem is not that the app needs a rewrite.
The problem is that a few concentrated seams are starting to slow safe iteration, increase regression risk, and blur which layer owns which behavior.

## Solution

Run a bounded refactor phase that stabilizes the most important seams without changing accepted product scope.
Keep the recommendation behavior, Amazon DE policy, pass-the-phone product shape, and current MVP decisions intact.
Make the backend API contract easier to trust, make route ownership clearer, make live TMDb candidate loading less wasteful, make tonight-intent provider wiring honest, and reduce pass-the-phone state sprawl.
Execute the work as narrow vertical slices with explicit ownership, validation commands, and stop conditions so autonomous agent runs can work safely.

## User Stories

1. As the founder, I want the refactor phase to preserve current product behavior, so that we improve maintainability without reopening accepted MVP decisions.
2. As the founder, I want one canonical API contract shape, so that frontend and backend changes stop drifting apart.
3. As the founder, I want API changes to fail fast in tests, so that contract regressions are caught before they reach the mobile flow.
4. As the founder, I want backend route ownership to be obvious, so that future changes do not require editing one giant file for unrelated work.
5. As a coding agent, I want route modules to own a coherent domain surface, so that I can work on one slice without scanning the whole API assembly file.
6. As a coding agent, I want dependency assembly to live in one predictable place, so that service wiring changes do not leak into endpoint definitions.
7. As the founder, I want the tonight-intent provider names to match what they actually do, so that product claims and code claims do not drift.
8. As a coding agent, I want deterministic and LLM-assisted interpretation paths to be explicitly separated, so that I can extend one without creating ambiguity in the other.
9. As the founder, I want live TMDb recommendation loading to stay fast enough for couch use, so that the app feels usable in a real session.
10. As the founder, I want TMDb fetch behavior to avoid unnecessary follow-up requests, so that live usage does not become fragile under rate limits or slow networks.
11. As a coding agent, I want candidate enrichment strategy to be explicit, so that performance tuning does not silently alter recommendation semantics.
12. As the founder, I want pass-the-phone state handling to be easier to inspect, so that UX changes do not create hidden regressions.
13. As a coding agent, I want wizard state grouped by subflow, so that setup, onboarding, steering, session sync, and results can evolve independently.
14. As the founder, I want autonomous agent runs to own narrow modules, so that parallel work does not create conflicts or force constant review interruptions.
15. As the founder, I want each refactor slice to have a stop condition and validation commands, so that autonomous work stops on evidence rather than vibes.
16. As a future maintainer, I want learning artifacts near the refactor work, so that the next person can understand the new boundaries quickly.
17. As the founder, I want to keep the current Prime Germany policy unchanged, so that this refactor phase does not accidentally reopen recent product decisions.
18. As the founder, I want current scoring behavior and shortlist semantics preserved unless a slice explicitly says otherwise, so that maintainability work does not mutate product output.
19. As the founder, I want the refactor phase to produce agent-ready execution slices, so that we can keep using bounded autonomous runs instead of broad manual cleanup.
20. As a coding agent, I want existing high-level tests to remain the primary guardrails, so that refactors stay behavior-first rather than implementation-first.

## Implementation Decisions

- The current phase is `MVP+7 Refactor Stabilization`.
- This is a stabilization phase, not a scope-expansion phase.
- Accepted MVP+6 product behavior remains the source behavior to preserve unless a future founder decision explicitly changes it.
- The highest-priority seams are:
  - API contract canonicalization
  - backend route extraction and assembly cleanup
  - tonight-intent provider honesty and separation
  - TMDb live candidate fetch budgeting
  - pass-the-phone state consolidation
- The backend API remains the source of truth for request and response contracts.
- The frontend should consume generated or centrally derived API contract types instead of continuing to hand-maintain large duplicate payload definitions.
- The backend app assembly file should retain application creation, dependency wiring, and route registration responsibilities only.
- Endpoint payload models and endpoint handler definitions should move toward route-focused modules grouped by domain surface.
- Route extraction should preserve existing URLs, response shapes, and validation behavior unless a slice explicitly documents a contract correction.
- Tonight-intent interpretation should expose a truthful distinction between deterministic interpretation and any optional LLM-assisted interpretation.
- If only directed nudges are LLM-assisted, the code and naming should say that plainly.
- Live TMDb fetching should introduce a deliberate enrichment budget.
- The fetch path should avoid full detail and provider follow-up calls for every discover candidate when a narrower staged enrichment strategy can preserve shortlist behavior.
- Any TMDb performance optimization must keep the current Amazon DE access rule intact:
  - Prime flatrate, rent, and buy all count as valid access when the title still passes the active language and watched-state rules.
- The pass-the-phone wizard should move toward a flow-oriented state model.
- The target shape is a reducer or equivalent explicit state transition layer that groups state by subflow rather than one growing component-level state surface.
- The refactor slices are:
  - Slice 1: API contract canonicalization and contract-generation seam
  - Slice 2: Backend route extraction and `create_app` assembly cleanup
  - Slice 3: Tonight-intent provider split and naming correction
  - Slice 4: TMDb live candidate fetch budgeting and caching seam
  - Slice 5: Pass-the-phone wizard state consolidation
- Slice 1 owns the canonical contract seam and should not attempt route extraction, scoring changes, or UI redesign.
- Slice 2 owns backend route organization and should not change product behavior or frontend flow semantics.
- Slice 3 owns provider semantics and should not broaden LLM product scope beyond the current accepted behavior.
- Slice 4 owns data-fetch structure and should not redefine Safe Pick rules or availability policy.
- Slice 5 owns frontend state organization and should not redesign the accepted mobile UX unless required to preserve current behavior.
- Learning artifacts should be updated alongside the refactor when a slice materially changes boundaries or operating guidance.

## Testing Decisions

- Good refactor tests verify externally visible behavior, not private implementation details.
- Existing API behavior, session flow behavior, shortlist behavior, steering behavior, and recommendation contract behavior are the guardrails to preserve.
- Contract changes should be tested at the highest seam possible:
  - backend API contract export or schema generation seam
  - frontend parsing and use of those contracts
  - contract tests that fail when response fields or enum values drift
- Route extraction should be validated by the same API tests that already cover onboarding, shortlist, sessions, setup, history, and steering.
- Tonight-intent refactoring should preserve the current interpreter behavior through existing tonight-intent tests plus targeted provider-wiring tests.
- TMDb fetch refactoring should use existing candidate-source tests and add focused tests around fetch budgeting, deduplication, and provider enrichment staging.
- Pass-the-phone refactoring should preserve the current mobile flow through existing app tests and focused behavior tests around setup, handoff, steering, shortlist loading, and results state.
- Prior art in the codebase includes:
  - API endpoint tests under the backend test suite
  - candidate-source and shortlist tests
  - tonight-intent interpretation tests
  - pass-the-phone smoke and flow validation
- Validation commands for autonomous slices should start with the repo baseline and then narrow to the owned seam when possible.
- Slice acceptance should prefer:
  - focused backend `unittest` targets for owned modules
  - backend compile checks
  - frontend build or targeted validation when the slice touches web code
  - existing smoke coverage when a slice materially affects the phone flow

## Out of Scope

- Rewriting the app from scratch.
- Changing accepted MVP product scope.
- Reopening the Amazon DE access decision.
- Reworking the scorer’s ranking policy or weights as part of this stabilization phase.
- Redesigning the pass-the-phone interface for visual polish alone.
- Introducing separate-phone shared sessions as part of this refactor phase.
- Broad infrastructure changes unrelated to the identified seams.
- Replacing TMDb with a different provider.
- Declaring new LLM product scope beyond the currently accepted steering path.

## Further Notes

- This phase is intended to make future feature work cheaper and safer, not to create a long abstract cleanup detour.
- Autonomous execution should begin with Slice 1 because it has the clearest ownership boundary and the strongest leverage on future regression risk.
- If Slice 1 reveals contract-generation tooling friction, that friction should be documented as part of the slice rather than hidden.
- If any slice exposes a true contradiction in accepted product behavior, the agent may surface the contradiction, but should not resolve it unilaterally.
- Assumption carried into this PRD:
  - the founder wants bounded autonomous refactor progress with minimal interruptions and no reopening of settled MVP behavior.
