# Post-seal production journey

- Date: 2026-08-13
- Web: `http://127.0.0.1:3125`
- API: `http://127.0.0.1:8000`
- Viewport: 390 x 844
- Browser: isolated headless Chrome through Playwright

## Claim

The current production build completes the ordinary two-person journey after the privacy-seal liveness correction, without exposing the first ballot during handoff or duplicating the final outcome submission.

## Observed journey

1. Initial onboarding state rendered `Checking taste setup`, not a false save or known `0 of 2` state.
2. Readiness resolved to an enabled `Start first pass` action.
3. The first private pass showed Arrival, Knives Out, The Grand Budapest Hotel, Edge of Tomorrow, and Past Lives in order.
4. The fifth Interested choice left the animated seal and reached `Ready for Husband`. The browser-observed wall time was 1,166 ms, including the vote write, render scheduling, the 520 ms seal, and transition into the handoff screen. The contract-level completion source remains capped at 650 ms.
5. Handoff exposed only the next person's name, privacy copy, and one Begin action. No title or reaction was visible.
6. The second person received the same five titles with a clean ballot.
7. After the fifth choice, matching completed and the ranked result appeared.
8. Arrival ranked first with five switchable titles, a real TMDB backdrop and posters, exact reaction wording, neutral genre evidence, and no percentage semantics.
9. Result Details opened with synopsis, exactly three cast members and roles, Why evidence, DE provider availability, and TMDB attribution. Escape closed it and restored focus to the exact Details opener.
10. Switching to Knives Out updated rank, title, metadata, and reason without a network call.
11. Five-more opened with whole-shell isolation, initial Close focus, honest offline steering copy, Escape close, and exact opener return.
12. Result options opened the shared watchlist, which rendered three entries and per-profile rating controls. Escape returned focus to the result-options opener.
13. After tonight exposed the exact three outcome choices. A rapid double activation of `Nothing tonight` produced exactly one outcome POST. The action settled to disabled `Saved`.
14. `Start new night` closed the utility surface and returned to the ordinary home with an enabled `Start first pass` action.

## Geometry and resilience observed

- Result viewport and document width were both 390 px.
- Result document height was exactly 844 px.
- All visible result controls measured at least 44 px in both dimensions.
- The ranked-result dock remained entirely visible: Details, Where to watch, and 5 more were each 54 px tall.
- The result backdrop and all five posters loaded with non-zero natural width.
- Result and utility modals isolated the app shell with both `inert` and `aria-hidden` and restored the exact opener on Escape.

## Evidence boundary

This trace proves the current single-process production journey and closes the reproduced privacy-seal hang. It does not make the process-local refresh-recovery vault suitable for multi-instance or cold-start deployment. S06 and S07 remain blocked on the founder architecture decision.

## Decision

Promote the post-seal journey evidence. Hold final S23 acceptance until the private recovery architecture is either made durable in the existing authenticated database or the refresh-recovery promise is removed.
