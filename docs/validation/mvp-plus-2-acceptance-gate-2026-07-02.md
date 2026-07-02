# MVP Plus 2 Acceptance Gate

Date: 2026-07-02

Phase: MVP+2 - Memory, Steering, And Rich Recommendation Intelligence

Status: Accepted.

## Recommendation-Quality Proof

The fixed evaluation command was regenerated:

```sh
python3 scripts/mvp_plus_2_evaluation.py
```

It writes:

- `docs/validation/mvp-plus-2-recommendation-quality.json`
- `docs/validation/mvp-plus-2-recommendation-quality.md`

Result summary:

- Baseline top pick: Dinner Party Mystery
- Enriched top pick: Edge of Tomorrow Again
- Target rank delta: +1
- Enrichment coverage: 2 of 4 candidates enriched, 2 fallback, 0.5 enrichment rate
- Recommendation-quality pass: true

The report includes rank deltas, top-pick changes, explanation excerpts, signal families, enrichment coverage, and risk notes.
It explicitly preserves fallback candidates and calls out mixed coverage and overfit risk.

## Phone-Sized Flow Proof

External desktop-browser smoke attempts were made first:

- Brave Browser aborted before DevTools with SIGABRT.
- Google Chrome also aborted before DevTools with SIGABRT.

The phone-sized proof was then completed in the Codex in-app browser at a 390 x 844 viewport against a fresh production web build on `http://127.0.0.1:3300`.

Observed click-through coverage:

- Profile identity visible as Husband + Wife.
- Profile memory panel visible with saved app memories, watched count, rated count, and private calibration signals.
- Tonight intent direct confirmation applied for "something funny from the 90s".
- Shared pass-the-phone flow completed through both participants.
- Results showed reranked shortlist, shared pick, and evidence entry points.
- Show 5 more loaded the next first-pass batch.
- Steer next 5 accepted “actually more action” and loaded the next first-pass batch from a fresh session.
- Shared watchlist add and remove were clicked from results.
- Watchlist rating controls were visible, and a watched/rated action updated the memory panel.

During this proof, the Show 5 more control was found to be mounted but visually collapsed.
The results action row was fixed so Show 5 more is the visible primary continuation action and Start new night is demoted.
The corrected production build was then rechecked in the phone viewport.

## Validation Commands

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
python3 scripts/mvp_plus_2_evaluation.py
```

Passed:

```sh
git diff --check
```

## Decision

MVP Plus 2 is complete after this acceptance slice is pushed and GitHub checks are green.

The accepted phase boundary remains 12 implementation slices.
No new issues were added to MVP Plus 2.
