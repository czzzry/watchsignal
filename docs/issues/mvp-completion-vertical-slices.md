# MVP Completion Vertical Slices

This issue set breaks [docs/prd-mvp-completion.md](../prd-mvp-completion.md) into bounded vertical slices.
It is prepared as local issue material and is not yet published to GitHub Issues.
Publishing these as GitHub issues is an external service action and should happen only after explicit approval.

## Slice 1 - Align Demo Fixture Contract

- Type: AFK
- Suggested labels: `mvp`, `ready-for-agent`, `tests`
- Blocked by: None
- Primary goal: restore a clean backend validation gate after the accepted demo candidate set changed.

### What to build

Update the fixture-facing backend tests and docs so they assert the accepted candidate contract from checkpoint `13835d0`.
The slice should preserve the candidate order, scoring behavior, Safe Pick behavior, and web-facing payload shape unless a failing test proves a real product mismatch.

### Owned areas

- `apps/api/tests/test_candidate_generation_adapter.py`
- `apps/api/tests/test_demo_couple_fixture.py`
- `apps/api/tests/test_shortlist_api.py`
- `docs/architecture/api-contracts.md`
- `docs/architecture/demo-couple-evaluation-fixture.md`

### Off-limits areas

- Accepted visual styling.
- Candidate ranking formula changes.
- Live TMDb calls.
- Live poster providers.
- Live critic-score providers.
- Private household data.

### Acceptance criteria

- [ ] Backend tests expect the accepted demo source IDs.
- [ ] Backend tests still prove rejected, unsafe, and already-watched fixture candidates do not leak into the main shortlist.
- [ ] Backend tests still prove Needs Quick Check items do not become the main shared recommendation by default.
- [ ] API contract docs no longer advertise the older synthetic shortlist as the current accepted demo payload.
- [ ] `pnpm check` passes.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when the backend fixture contract agrees with the accepted demo shortlist and the API validation gate is clean.

### Risk notes

Do not make the tests pass by changing ranking logic unless the accepted demo contract itself is wrong.
This slice is meant to align tests and docs to the accepted behavior, not change the behavior.

## Slice 2 - Preserve Accepted UI Refactor And Run Local UX Gate

- Type: HITL for final browser proof, AFK for code and docs verification
- Suggested labels: `mvp`, `ui`, `validation`
- Blocked by: Slice 1 recommended, but not strictly required
- Primary goal: prove that the accepted cinematic UI refactor is ready to merge without behavior drift.

### What to build

Keep the current component, helper, model, and CSS sectioning refactor intact.
Run the non-browser checks in the agent environment and run the phone-sized browser smoke in a normal local browser environment.
Capture what was clicked, what passed, and any visible rough edges.

### Owned areas

- `apps/web/app/pass-the-phone-wizard.tsx`
- `apps/web/app/pass-the-phone-components.tsx`
- `apps/web/app/pass-the-phone-helpers.ts`
- `apps/web/app/pass-the-phone-model.ts`
- `apps/web/app/globals.css`
- `docs/setup/mobile-pass-the-phone-ux-smoke.md`

### Off-limits areas

- Visual redesign away from checkpoint `13835d0`.
- Rollback to checkpoint `ab5568f`.
- Backend scoring changes.
- Live provider integration.

### Acceptance criteria

- [ ] TypeScript check passes for the web app.
- [ ] Web production build passes.
- [ ] API compile check passes.
- [ ] Phone-sized browser smoke completes on a normal local browser.
- [ ] The click-through covers Launch, Setup, Reaction, Handoff, and Results.
- [ ] The summary records whether the flow used demo mode or backend-backed mode.

### Validation commands

```sh
pnpm build:web
```

```sh
pnpm compile:api
```

```sh
pnpm smoke:ux:mobile
```

### Stop condition

Stop when the accepted UI has a clean build and a recorded phone-sized click-through result.

### Risk notes

Browser startup failures inside the agent sandbox should be recorded as environment failures.
They should not be treated as product failures unless the same flow fails in a normal local browser.

## Slice 3 - Make Demo Data Provenance Honest

- Type: AFK, with HITL only if visible main-flow copy changes
- Suggested labels: `mvp`, `trust`, `fixtures`
- Blocked by: Slice 1
- Primary goal: prevent demo fixture values from being mistaken for live sourced data.

### What to build

Keep local poster assets and fixture scores available for the accepted demo.
Add or tighten code-facing and doc-facing provenance so future agents know which fields are local demo assets, hard-coded fixture values, API payload values, or unavailable.
Only change visible UI copy if the current UI clearly implies live sourcing.

### Owned areas

- `apps/web/app/pass-the-phone-model.ts`
- `apps/web/app/pass-the-phone-helpers.ts`
- `apps/web/app/session-fixtures.ts`
- `docs/architecture/mobile-pass-the-phone-wizard.md`
- `docs/prd-mvp-completion.md`

### Off-limits areas

- Main visual redesign.
- Live poster provider wiring.
- Live critic-score provider wiring.
- Live availability provider wiring.
- LLM explanation copy.

### Acceptance criteria

- [ ] Candidate view models expose poster and critic-score provenance where the UI needs it.
- [ ] Docs state that local poster assets are demo assets.
- [ ] Docs state that critic scores are fixture values.
- [ ] Docs state that no live poster or critic-score provider is wired into local demo mode.
- [ ] Normal demo behavior and visual design are preserved.
- [ ] Web production build passes if frontend files change.

### Validation commands

```sh
pnpm build:web
```

```sh
pnpm check
```

### Stop condition

Stop when demo provenance is explicit without changing the accepted experience.

### Risk notes

Visible provenance copy can quickly make the pass-the-phone flow feel like an internal test harness.
Prefer code and docs first unless the UI is actively misleading.

## Slice 4 - Prove Backend-Backed Local Couch Flow

- Type: AFK where the environment can launch a browser, otherwise HITL for final smoke
- Suggested labels: `mvp`, `validation`, `local-web`
- Blocked by: Slices 1 and 2
- Primary goal: prove the MVP flow against isolated local storage, not just demo fallback state.

### What to build

Run and, if necessary, repair the backend-backed local smoke path.
The flow should seed safe default setup data, start a shared session, collect both reaction passes, rerank, record outcome, record post-watch feedback, and inspect debug history.
It must use an isolated temporary database.

### Owned areas

- `scripts/mobile_pass_the_phone_ux_smoke.mjs`
- `scripts/couch_flow_smoke.py`
- `apps/web/app/session-client.ts`
- `apps/web/app/api/session/**`
- `apps/api/src/movie_night_mediator/app/session.py`
- `apps/api/src/movie_night_mediator/app/outcome.py`
- `apps/api/src/movie_night_mediator/app/feedback.py`
- `apps/api/src/movie_night_mediator/app/debug_history.py`
- Related tests in `apps/api/tests`

### Off-limits areas

- Visual redesign.
- Live provider calls.
- Persistent real household database writes.
- LLM interpretation.

### Acceptance criteria

- [ ] Backend-backed smoke uses an isolated temporary SQLite database.
- [ ] Both participants can submit reactions.
- [ ] Handoff state is exercised.
- [ ] Results include a best pick and reranked shortlist.
- [ ] Outcome capture succeeds.
- [ ] Per-person post-watch feedback succeeds.
- [ ] Debug history shows persisted evidence.
- [ ] `MOBILE_UX_SMOKE_EXPECT_API=1 pnpm smoke:ux:mobile` passes in a normal local browser environment.

### Validation commands

```sh
python3 scripts/couch_flow_smoke.py
```

```sh
MOBILE_UX_SMOKE_EXPECT_API=1 pnpm smoke:ux:mobile
```

### Stop condition

Stop when the local backend-backed pass-the-phone flow is proven without touching real household data.

### Risk notes

The highest risk is accidentally pointing the smoke at the real local database.
The command must make temporary storage explicit.

## Slice 5 - Clarify Live Candidate Provider MVP Gate

- Type: HITL decision, then AFK implementation planning
- Suggested labels: `mvp`, `product-decision`, `provider`
- Blocked by: Slices 1 through 4
- Primary goal: decide whether the first declared MVP is demo-complete or live-candidate usable.

### What to build

Produce a short decision note that reconciles the existing architecture statement that live TMDb is required before the app is usable with the current accepted local demo UI.
If the founder confirms that live candidate sourcing is still required for MVP, break that work into a separate implementation issue set.
If the founder decides the local demo MVP can close first, explicitly mark live candidate sourcing as the next MVP readiness phase rather than MVP plus 1.
This pass records the gate only and does not create live-provider implementation issues unless the founder explicitly asks for that work.

### Owned areas

- `docs/architecture/code-first-app-architecture.md`
- `docs/prd-code-first-mvp.md`
- `docs/prd-mvp-completion.md`
- `docs/issues/mvp-completion-vertical-slices.md`
- A future provider issue file if approved

### Off-limits areas

- Provider implementation before the decision is recorded.
- Critic-score provider implementation.
- Paid vendor commitments.
- Secrets or credentials.

### Acceptance criteria

- [ ] The repo states whether live candidate sourcing is required before the MVP is called usable.
- [ ] The repo separates live poster, live critic score, and live candidate-provider concerns.
- [ ] Any provider implementation issues include credential needs, network needs, owned files, off-limits files, and validation commands.
- [ ] No external service change happens without approval.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when the founder-facing MVP gate is explicit and no one can confuse MVP completion with MVP plus 1 LLM work.

### Risk notes

This is the one remaining slice that may need founder judgment.
The existing docs lean toward live TMDb being MVP-required, but the recent accepted UI work is a local demo flow.

## Slice 6 - Publish MVP Completion Issues To GitHub

- Type: HITL
- Suggested labels: `process`, `issues`
- Blocked by: Founder approval to publish issues
- Primary goal: turn this local issue file into tracker issues once the founder wants GitHub to become the working queue.

### What to build

Create one GitHub issue for each accepted slice.
Preserve the objective, owned areas, off-limits areas, acceptance criteria, validation commands, and stop condition.
Apply the agreed labels after confirming the labels exist or can be created.

### Owned areas

- GitHub Issues
- `docs/issues/mvp-completion-vertical-slices.md`

### Off-limits areas

- Source changes unrelated to issue publication.
- Remote pushes.
- PR creation.
- Label taxonomy changes without approval.

### Acceptance criteria

- [ ] Each approved slice has a GitHub issue.
- [ ] Each issue links back to the local PRD or issue-slice doc.
- [ ] Each issue has clear validation commands.
- [ ] No issue includes MVP plus 1 implementation scope unless explicitly approved.

### Validation commands

```sh
gh issue list
```

### Stop condition

Stop when the approved local slices exist as GitHub issues and the local docs link to them if desired.

### Risk notes

Publishing issues is an external service change.
Do not do it as part of ordinary local doc cleanup.

## Recommended First Implementation Slice

Start with Slice 1.
It has the narrowest blast radius and clears the known test drift caused by the accepted candidate set.
It should not touch the accepted UI visuals, live providers, or product scope.
