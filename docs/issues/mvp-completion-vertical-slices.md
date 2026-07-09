# MVP+6 Vertical Slices

This issue set refreshes [docs/prd-mvp-completion.md](../prd-mvp-completion.md) against the later accepted validation trail in MVP+3, MVP+4, and MVP+5.
It is the working issue plan for closing stale docs, encoding the current Amazon DE availability decision, and keeping future agent work low-touch and independently executable.
It is prepared as local issue material first so the published GitHub issues match current product decisions instead of older intermediate assumptions.

## Published GitHub Tracker

- #105 - MVP+6 Slice 1 - Reconcile MVP source of truth and retire stale gate assumptions
- #106 - MVP+6 Slice 2 - Update Amazon DE watchability policy with TDD
- #107 - MVP+6 Slice 3 - Align demo and live candidate contracts to the updated availability rule
- #108 - MVP+6 Slice 4 - Record current validation coverage and tighten the remaining local UX gate
- #109 - MVP+6 Slice 5 - Decide the remaining live-usable MVP gate after the Amazon DE rule
- #110 - MVP+6 Slice 6 - Publish and maintain the refreshed GitHub queue

## Current Phase

MVP+6: [██████] 6/6 issues closed.

The repo already has accepted validation for major product-flow proof in:

- `docs/validation/mvp-plus-3-acceptance-gate-2026-07-07.md`
- `docs/validation/mvp-plus-4-acceptance-gate-2026-07-07.md`
- `docs/validation/mvp-plus-5-acceptance-gate-2026-07-07.md`

This issue set should not pretend those gates did not happen.
Instead, it should reconcile stale planning docs, tighten current contracts, and record the remaining MVP-readiness questions honestly.

## Founder Decision Now In Scope

Amazon DE availability should count as valid whether the title is subscription, rental, or purchase.
Do not downgrade Amazon DE rental or purchase titles to `Needs Quick Check` solely because they are paid rather than included in subscription.
Continue to enforce the other active rules such as language compatibility, watched-state filtering, and any future manual watchability correction logic.

## Agent Execution Posture

Write and publish these issues so an agent can work as independently as possible.
Each AFK issue should prefer local code and doc changes, local validation commands, and no network dependency unless the issue is explicitly about GitHub publication or a founder-facing decision note.
If a later implementation issue truly requires external permissions, it should say so once, early, and in one batched request rather than through repeated prompts.

## Treehouse Posture

Treehouse fanout is appropriate for thin AFK slices with clear blockers and stable contracts.
Treehouse is not the default for HITL decision slices or any slice that would amplify noisy permission prompts.
The best Treehouse candidates in this set are Slices 1, 2, 3, and 4 after blockers are satisfied.

## Slice 1 - Reconcile MVP Source Of Truth And Retire Stale Gate Assumptions

- Type: AFK
- Suggested labels: `mvp`, `ready-for-agent`, `docs`
- Blocked by: None
- Treehouse candidate: yes
- Primary goal: make the repo's local planning docs reflect the accepted validation trail and current product posture.

### What to build

Update the MVP-completion planning docs so they stop describing already-accepted validation work as future work.
Record that MVP+3 and MVP+4 already proved real phone-sized dogfood paths, and that MVP+5 passed deterministic checks with the remaining local mobile block recorded as an environment limitation rather than a hidden product failure.
Use this slice to make later implementation issues trustworthy.

### Owned areas

- `docs/issues/mvp-completion-vertical-slices.md`
- `docs/prd-mvp-completion.md`
- `docs/validation/live-usable-mvp-gate-2026-06-30.md`
- Other small planning or validation-note docs if needed to remove direct contradictions

### Off-limits areas

- Backend recommendation logic
- UI redesign
- Provider integration changes
- GitHub issue publication

### Acceptance criteria

- [ ] Local planning docs no longer describe already-accepted MVP+3 or MVP+4 product-flow proof as undone work.
- [ ] MVP+5 local browser blocking is described as an environment limitation where that distinction matters.
- [ ] The refreshed docs make clear which work is historical proof, which work is current cleanup, and which work is still an open decision.
- [ ] `pnpm check` still passes if code-facing docs or tests are touched.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when a new reader can understand current state without being misled by older MVP-completion language.

### Risk notes

Do not rewrite accepted history.
Reconcile it.

## Slice 2 - Update Amazon DE Watchability Policy With TDD

- Type: AFK
- Suggested labels: `mvp`, `ready-for-agent`, `tdd`, `provider`
- Blocked by: Slice 1 recommended, but not strictly required
- Treehouse candidate: yes
- Primary goal: encode the founder decision that Amazon DE access counts whether the title is flatrate, rent, or buy.

### What to build

Write failing tests first for the new Amazon DE rule.
Then update the watchability classifier, shortlist behavior, fixtures, and decision docs so Amazon DE titles remain eligible when they satisfy the other active filters.
Language compatibility, watched-state filtering, and explicit manual watchability decisions should still behave normally.

### Owned areas

- `apps/api/src/movie_night_mediator/app/safe_pick.py`
- `apps/api/src/movie_night_mediator/adapters/tmdb_candidate_source.py`
- Related tests in `apps/api/tests`
- `docs/architecture/safe-pick-decision-table.md`
- Any nearby contract or validation docs that explicitly mention the old subscription-only rule

### Off-limits areas

- Paid vendor additions
- New live provider integrations beyond current TMDb usage
- Broad scoring changes unrelated to watchability classification
- UI redesign

### Acceptance criteria

- [ ] Tests are added first for Amazon DE flatrate, rent, and buy eligibility.
- [ ] Amazon DE rent-only or buy-only access no longer becomes `Needs Quick Check` solely due to being paid access.
- [ ] English audio, subtitle, watched-state, and manual correction rules still behave as intended.
- [ ] The docs no longer describe Amazon DE paid access as subscription-invalid by default.
- [ ] `pnpm check` passes.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when Amazon DE access is treated the way the founder requested and the rule is locked in by tests.

### Risk notes

Do not silently broaden the decision beyond Amazon DE wording unless the tests and docs make that scope explicit.

## Slice 3 - Align Demo And Live Candidate Contracts To The Updated Availability Rule

- Type: AFK
- Suggested labels: `mvp`, `ready-for-agent`, `tests`, `fixtures`
- Blocked by: Slice 2
- Treehouse candidate: yes
- Primary goal: make fixture tests, live-source tests, and shortlist docs agree on the current candidate contract after the Amazon DE rule change.

### What to build

Update the fixture-facing and live-source tests so they assert the accepted shortlist shape and provider semantics under the new availability rule.
Keep the candidate order, scoring behavior, and web-facing payload shape stable unless a failing test proves a real contract mismatch.

### Owned areas

- `apps/api/tests/test_candidate_generation_adapter.py`
- `apps/api/tests/test_demo_couple_fixture.py`
- `apps/api/tests/test_shortlist_api.py`
- `apps/api/tests/test_tmdb_candidate_source.py`
- `docs/architecture/api-contracts.md`
- `docs/architecture/demo-couple-evaluation-fixture.md`

### Off-limits areas

- Accepted visual styling
- Broad recommendation-score retuning
- Live poster providers
- Live critic-score providers
- Private household data

### Acceptance criteria

- [ ] Backend tests expect the accepted demo source IDs and current provider semantics.
- [ ] Tests still prove rejected, unsafe, and already-watched candidates do not leak into the main shortlist.
- [ ] Tests and docs no longer encode the old Amazon DE subscription-only interpretation.
- [ ] API contract docs describe the accepted shortlist payload honestly.
- [ ] `pnpm check` passes.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when the backend fixture and live-source contract agree with the accepted shortlist and updated watchability rule.

### Risk notes

Do not make tests pass by casually changing ranking behavior.
Contract alignment should be driven by the intended product rule, not by convenience.

## Slice 4 - Record Current Validation Coverage And Tighten Remaining Local UX Gate

- Type: HITL for a normal local browser rerun if needed, AFK for code and docs verification
- Suggested labels: `mvp`, `validation`, `local-web`
- Blocked by: Slices 1 and 3
- Treehouse candidate: limited
- Primary goal: document exactly what has already been proven and what narrow founder-side validation still remains.

### What to build

Refresh the local validation story so it reflects the accepted MVP+3 through MVP+5 trail and the updated Amazon DE behavior.
If the normal local browser rerun is still needed after the policy change, keep it narrow and explicit.
Do not restate broad backend-backed proof as if it never happened.

### Owned areas

- `docs/validation/live-usable-mvp-gate-2026-06-30.md`
- `docs/setup/mobile-pass-the-phone-ux-smoke.md`
- `scripts/mobile_pass_the_phone_ux_smoke.mjs` only if the gate itself needs a small fix
- Small related validation docs if they directly contradict accepted history

### Off-limits areas

- Visual redesign
- New product scope
- Provider expansion beyond the accepted rule change
- Persistent real household database writes

### Acceptance criteria

- [ ] The validation docs distinguish historical accepted proof from any remaining manual rerun clearly.
- [ ] Any remaining founder-side click-through is described as a narrow confirmation step, not as missing end-to-end proof from scratch.
- [ ] If smoke code changes are needed, they stay limited to validation reliability rather than feature work.
- [ ] `pnpm check` passes if validation scripts are touched.

### Validation commands

```sh
pnpm check
```

```sh
MOBILE_UX_SMOKE_EXPECT_API=1 pnpm smoke:ux:mobile
```

### Stop condition

Stop when the repo says exactly what has been proven and exactly what, if anything, still needs a normal-browser confirmation.

### Risk notes

Do not reopen settled product questions here.
This slice is about evidence and clarity.

## Slice 5 - Decide The Remaining Live-Usable MVP Gate After The Amazon DE Rule

- Type: HITL decision, then AFK doc follow-through
- Suggested labels: `mvp`, `product-decision`, `provider`
- Blocked by: Slices 1 through 4
- Treehouse candidate: no
- Primary goal: record whether the remaining live-usable MVP definition is now satisfied or still awaits one specific founder-side confirmation.

### What to build

Produce a short decision note that reconciles the current accepted gates, the live TMDb path, and the new Amazon DE access policy.
If the founder still wants one more normal-browser rerun before calling the app live-usable MVP, record that as the last narrow gate.
If not, record the app as live-usable MVP with any remaining work reclassified as next-phase polish rather than false MVP incompleteness.

### Owned areas

- `docs/prd-mvp-completion.md`
- `docs/validation/live-usable-mvp-gate-2026-06-30.md`
- `docs/architecture/code-first-app-architecture.md`
- `docs/issues/mvp-completion-vertical-slices.md`
- A short new decision note if that is cleaner than further patching old docs

### Off-limits areas

- New provider implementation
- Critic-score provider implementation
- Paid vendor commitments
- Secrets or credentials

### Acceptance criteria

- [ ] The repo states clearly whether the app is already live-usable MVP or what one remaining gate still blocks that label.
- [ ] The repo separates live candidate sourcing, poster sourcing, critic-score sourcing, and watchability policy decisions cleanly.
- [ ] The docs no longer confuse MVP readiness with MVP plus 1 or later recommendation work.
- [ ] No external service change happens as part of this decision note.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when the founder-facing MVP status is explicit and reviewable.

### Risk notes

This slice is allowed to conclude that the old gate language is now stale.
It does not need to preserve outdated ambiguity.

## Slice 6 - Publish Refreshed MVP+6 Issues To GitHub

- Type: HITL approved, AFK execution
- Suggested labels: `process`, `issues`
- Blocked by: Founder approval to publish issues
- Treehouse candidate: no
- Primary goal: publish the refreshed slices as low-touch, agent-ready GitHub issues in dependency order.

### What to build

Create one GitHub issue for each accepted slice.
Write them so an agent can work independently with local validation, minimal network needs, and explicit blocker handling.
Where an issue may need external permissions later, say so once and ask future agents to batch permission requests early instead of repeatedly.

### Owned areas

- GitHub Issues for `czzzry/watchsignal`
- `docs/issues/mvp-completion-vertical-slices.md`

### Off-limits areas

- Source changes unrelated to issue publication
- Remote pushes
- PR creation
- Label taxonomy changes without approval

### Acceptance criteria

- [ ] Each approved slice has a GitHub issue in dependency order.
- [ ] Each issue is worded as a vertical slice with clear acceptance criteria and blocker handling.
- [ ] Each issue tells future agents to batch unavoidable permission asks early rather than surfacing repeated prompts.
- [ ] Treehouse-suitable AFK issues are obvious from the published wording.

### Validation commands

```sh
gh issue list
```

### Stop condition

Stop when the refreshed local slices exist as publish-ready GitHub issues and the wording supports low-touch independent execution.

### Risk notes

Publishing issues is an external service change.
Do not let the published wording drift from the refreshed local source of truth.

## Recommended First Implementation Slice

Start with Slice 2.
It encodes the active founder decision, benefits from TDD immediately, and will unblock the remaining contract and validation cleanup from the right product rule.
