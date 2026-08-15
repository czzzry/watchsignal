# S18 round 4 evidence handoff

## Claim

One person can privately teach WatchSignal one movie at a time, and a failed remote save never discards the selected choice.

## Production pair

FastAPI `127.0.0.1:8018` and built Next.js `127.0.0.1:3118` were started from the same current worktree.
The captured page contains no Next.js development overlay.

## Browser evidence

- `taste-lab-clean-390x844.png`: clean current production surface.
- `keyboard-traversal.json`: real forward and reverse keyboard traversal.
- `deterministic-first-failure.png`: first induced POST failure with Loved retained.
- `deterministic-retry-success.png`: Retry succeeded and advanced to the next title.
- `deterministic-second-failure.png`: second induced POST failure with Not for me retained.
- `deterministic-keep-local-success.png`: Keep on this phone advanced and confirmed local retention.
- `deterministic-save-recovery-trace.json`: three POST attempts in exact order: failed, succeeded, failed; final local action issued no fourth POST.

The round 2 responsive, missing-poster, 200-percent, reduced-mode, and forced-colors evidence remains valid because round 4 made no production changes.

## Validation

- Focused S18 web tests: 5 of 5 passed.
- Focused Taste Lab API tests: 17 passed.
- Full web state tests: 178 passed.
- Full API tests: 351 passed.
- TypeScript: passed.
- Production build was still running at forced handoff after entering optimized compilation.

## Boundary

No production files changed in round 4.
This is an evidence handoff for an independent critic, not an acceptance claim.
