# S17 round 8 evidence handoff

## Production pair

FastAPI `127.0.0.1:8018` and built Next.js `127.0.0.1:3118` ran from the same current worktree.
The production frontend was restarted after build completion to eliminate stale client chunks.

## 200-percent evidence

The `actual-*` captures use a 195 by 422 CSS-pixel viewport at device scale factor 2, producing a real 390 by 844 physical-pixel 200-percent-equivalent state.

- Live list and settled detail are captured.
- Error and Retry are captured.
- Missing-poster list and settled fallback detail are captured.
- Header, primary content, and footer controls exist in every state and are reachable through normal scrolling.
- Row to detail to Back restores the same Arrival list row.
- There is no horizontal overflow: document scroll width equals the 195 CSS-pixel viewport.

`actual-browser-evidence.json` records the measurements.
`focus-return.json` records a remaining accessibility defect: the Recent nights opener has exact focus before opening, but Escape leaves focus on `BODY` rather than returning to the exact opener at this viewport.

The earlier CSS-zoom captures are retained for transparency.
They show header truncation (`Rec...` and `Arri...`) and underlying setup content visible above and below the enlarged sheet.
Those images are not claimed as successful 200-percent reflow evidence.

## Boundary

No production files changed in round 8.
This evidence is for a separate critic and contains no acceptance claim.
