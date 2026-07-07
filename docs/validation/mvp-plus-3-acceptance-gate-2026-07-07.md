# MVP Plus 3 Acceptance Gate

Date: 2026-07-07

Phase: MVP+3 - Directed Discovery And Real Tester Profile

Issue status: 9/10 implementation issues done.

Status: Not accepted yet.

## Decision

MVP Plus 3 is not complete yet because the required phone-sized browser smoke did not pass in this local environment.
The product implementation is materially complete through issue #71, and the recommendation-quality proof passes.
The remaining blocker is #72 phone-sized browser proof.

## Product-Flow Proof

The backend-backed dogfood smoke was upgraded to seed and verify the MVP Plus 3 profile path before opening the browser:

- Creates `Cezary - tester` through the setup API.
- Promotes `Cezary - tester` into the first participant slot.
- Keeps the default partner profile as the second participant.
- Seeds onboarding for both active participants.
- Saves a Taste Lab `loved` rating for `Cezary - tester`.
- Reads the tester Taste Lab summary and verifies at least one preference evidence signal.
- Starts a production web build and temporary backend database for the dogfood run.
- Asserts that the result screen exposes `Current signals` and `Cezary - tester: 1 signals` when the browser run can proceed.

The browser portion did not complete because every available local browser launch path failed before a stable DevTools session was available.

Attempts:

- `pnpm beta:dogfood` with Brave Browser failed with `SIGABRT` before DevTools.
- `CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" pnpm beta:dogfood` failed with `SIGABRT` before DevTools.
- Repo-local Playwright headless shell launched further after adding headless-safe flags, then failed with a macOS Mach port rendezvous permission error.
- Repo-local Chrome for Testing failed with `SIGABRT` before DevTools.

## Recommendation-Quality Proof

The fixed evaluation command passed:

```sh
python3 scripts/mvp_plus_3_evaluation.py
```

It writes:

- `docs/validation/mvp-plus-3-recommendation-quality.json`
- `docs/validation/mvp-plus-3-recommendation-quality.md`

Result summary:

- Baseline top pick: Cozy Mystery Night
- Enriched top pick: The Shining
- Target rank delta: +1
- Top pick changed: true
- Recommendation-quality pass: true

The report includes rank deltas, top-pick changes, explanation excerpts, signal families, matched person names, and caveats.
It proves that tester profile calibration plus a directed nudge can change ranking and expose Taste Lab plus tonight-intent evidence.

## Validation Commands

Passed:

```sh
pnpm beta:preflight
```

Warnings were expected in this dirty local slice:

- `API_BASE_URL` was unset.
- TMDb credentials were unset.
- The worktree had local #72 changes.

Passed:

```sh
pnpm build:web
```

Passed:

```sh
python3 scripts/mvp_plus_3_evaluation.py
```

Failed:

```sh
pnpm beta:dogfood
```

Reason: local browser startup failed before the script could complete phone-sized UX proof.

## Open Risks

- Phone-sized browser proof remains open.
- The upgraded smoke seed path has not completed end to end because browser startup is blocked.
- Live TMDb actor coverage was not revalidated because TMDb credentials are not present in this environment.
- The recommendation-quality report is deterministic and local; it is not a broad recommendation benchmark.

## Recommended Next Step

Run `pnpm beta:dogfood` on a machine or browser surface where Chromium DevTools can start successfully.
Once that passes, update this note to accepted, mark #72 done, close #72, and update the MVP Plus 3 tracker to 10/10.
