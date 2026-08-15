# S18 round 5 evidence handoff

## Claim

After Retry or any candidate advance, the visible title and poster always belong to the same current movie.

## Contract and boundary

The active movie ID keys the image element and the ready-poster state.
On movie change, poster readiness resets.
The current poster stays visually hidden until that exact image loads, while an intentional current-title loading placeholder occupies the frame.
Queue, save, Retry, local retention, profile, and API semantics are unchanged.

## Production evidence

FastAPI `127.0.0.1:8018` and rebuilt Next.js `127.0.0.1:3118` ran from the same current worktree.

- `current-title-poster-loading-corrected.png` shows the new title with its intentional loading placeholder and no prior art.
- `current-title-poster-steady-corrected.png` shows the same title after its matching poster loads.
- `corrected-poster-gate.json` records `hiddenWhileLoading: true`, `visibleAfterLoad: true`, the current image URL, and two POST attempts: induced failure followed by Retry success.
- The real recovery keyboard order reaches Keep on this phone, Try again, then Taste Lab progress.

The earlier `loading-gate-and-keyboard.json` is retained for transparency but is superseded because it exposed the stylesheet override that made a hidden image visible.

## Validation

- Focused S18 web tests: 6 of 6 passed.
- TypeScript: passed.
- Production build completed and wrote a new `BUILD_ID` at 03:45:56.
- Diff check: passed.

## Masked comparison

Seed: `1805`.
The independent critic should inspect `masked-pair/screen-1.png`, `screen-2.png`, and `screen-3.png` before reading `masked-pair/unblind.txt`.

This is a builder handoff and contains no acceptance claim.
