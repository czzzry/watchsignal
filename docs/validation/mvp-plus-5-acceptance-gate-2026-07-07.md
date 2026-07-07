# MVP Plus 5 Acceptance Gate

Date: 2026-07-07

Phase: MVP+5 - Household Taste Memory

Issue status: 7/7 implementation issues represented in this gate.

Status: Accepted deterministic checks; mobile dogfood blocked locally.

## Issue List

- #91 Persist profile taste memory events

- #92 Use taste memory in recommendation scoring

- #93 Add Profile Taste Ledger

- #94 Add before and after taste snapshot

- #95 Improve Taste Lab calibration queue

- #96 Upgrade recommendation trust UI

- #97 Add Household Taste Memory acceptance gate

## Command Summary

Live TMDb credentials available: yes.

Mobile dogfood command selected: `pnpm beta:dogfood:live`.

| Check | Command | Result | Duration |

| --- | --- | --- | --- |

| Beta readiness preflight | `pnpm beta:preflight` | passed | 2s |

| API tests and compile | `pnpm check` | passed | 12s |

| Web production build | `pnpm build:web` | passed | 15s |

| MVP+5 household taste memory evaluation | `pnpm eval:mvp5` | passed | 2s |

| Live TMDb mobile dogfood | `pnpm beta:dogfood:live` | blocked | 2s |

## Evaluation Coverage

Issues represented: 7/7.

Required scenarios present: true.

Strict required scenarios passed: true.

Calibration queue improves coverage: true.

Memory before and after passed: true.

## Mobile Dogfood Coverage

- Command runs the backend-backed mobile pass-the-phone smoke.

- Smoke path seeds tester and partner profiles, creates memory, inspects ledger or snapshot text, checks trust UI, and exercises watchlist and post-watch feedback.

- In this local sandbox, server binding may fail with `listen EPERM`; that is recorded as blocked rather than hidden.

## Open Risks

- Live mobile dogfood still needs to be rerun in an environment that can bind localhost.

- Live TMDb dogfood was selected because TMDb credentials were available.

## Command Tail: Live TMDb mobile dogfood

```text

[ELIFECYCLE] Command failed with exit code 1.

[ELIFECYCLE] Command failed with exit code 1.

$ MOVIE_NIGHT_RECOMMENDATION_SOURCE=live_tmdb MOBILE_UX_SMOKE_EXPECT_API=1 MOBILE_UX_SMOKE_EXPECT_RECOMMENDATION_SOURCE=live_tmdb pnpm smoke:ux:mobile

$ node scripts/mobile_pass_the_phone_ux_smoke.mjs

listen EPERM: operation not permitted 127.0.0.1

```
