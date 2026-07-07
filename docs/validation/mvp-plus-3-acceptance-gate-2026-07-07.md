# MVP Plus 3 Acceptance Gate

Date: 2026-07-07

Phase: MVP+3 - Directed Discovery And Real Tester Profile

Issue status: 10/10 implementation issues done.

Status: Accepted.

## Decision

MVP Plus 3 is complete.
The phase has both product-flow proof and recommendation-quality proof.
No new MVP Plus 3 scope was added during acceptance.

## Product-Flow Proof

The backend-backed dogfood smoke now seeds and verifies the MVP Plus 3 profile path before opening the browser:

- Creates `Cezary - tester` through the setup API.
- Promotes `Cezary - tester` into the first participant slot.
- Keeps the default partner profile as the second participant.
- Seeds onboarding for both active participants.
- Saves a Taste Lab `loved` rating for `Cezary - tester`.
- Reads the tester Taste Lab summary and verifies at least one preference evidence signal.
- Starts a production web build and temporary backend database for the dogfood run.
- Asserts that the result screen exposes `Current signals` and `Cezary - tester: 1 signals`.

The completed phone-sized run used a normal Chrome app instance with DevTools already open:

```sh
open -na "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir=/private/tmp/movie-night-mediator-chrome-9222 --no-first-run --no-default-browser-check about:blank
```

Then the dogfood command was run against that browser:

```sh
MOBILE_UX_SMOKE_DEBUGGING_URL=http://127.0.0.1:9222 pnpm beta:dogfood
```

Observed coverage:

- Temporary backend and production web server started.
- `Cezary - tester` profile was created and used as the first active participant.
- Taste Lab evidence was seeded and visible in the result evidence panel.
- Main pass-the-phone recommendation flow completed through both participants.
- Watchlist add, watched, and remove actions completed.
- Session outcome was saved.
- Post-watch feedback was saved for `Cezary - tester` and `Husband`.
- Recent-session history reloaded and showed session outcome, feedback, and reaction evidence.
- Viewport was 390 x 844 mobile.

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

Passed:

```sh
pnpm check
```

Passed:

```sh
pnpm build:web
```

Passed:

```sh
python3 scripts/mvp_plus_3_evaluation.py
```

Passed:

```sh
MOBILE_UX_SMOKE_DEBUGGING_URL=http://127.0.0.1:9222 pnpm beta:dogfood
```

## Closed Risks

- Phone-sized browser proof passed through a normal Chrome DevTools session.
- The upgraded smoke seed path completed end to end.
- Visible result evidence now fetches Taste Lab summaries immediately after session creation and continuation.
- Profile labels in post-watch feedback smoke now match the MVP Plus 3 tester-profile flow.

## Remaining Caveats

- Live TMDb actor coverage was not revalidated because TMDb credentials are not present in this environment.
- The recommendation-quality report is deterministic and local; it is not a broad recommendation benchmark.

These are not MVP Plus 3 blockers.
They should be treated as next-phase validation depth, not unfinished MVP Plus 3 scope.
