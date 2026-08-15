# S17 round 7 evidence handoff

Claim: household history remains recognizable and usable without exposing diagnostic session data.

Production pair: FastAPI `127.0.0.1:8018` and built Next.js `127.0.0.1:3118`, started from the same current worktree.

Captured evidence is in `../round-6/` because the round 7 run completed the interrupted round 6 capture grid without changing production code.

- Live list and detail: 320x844, 390x844, 430x844, 390x568, and emulated 200% reflow.
- Error list: the same five viewports.
- Missing-poster list and settled detail: the same five viewports.
- Settled approved-poster detail: `safe-poster-390x844-detail.png`.
- Active modes: `reduced-motion-list.png`, `reduced-transparency-list.png`, and `forced-colors-list.png`.
- Every completed responsive measurement had document scroll width equal to viewport width.
- Back returned from detail to the existing list.
- Escape closed the modal and returned focus to the Recent nights opener.
- Consumer list keys verified from the current API: `historyHandle`, `occurredAt`, `outcomeLabel`, `posterUrl`, `title`.

The first live detail screenshots record the honest loading state while the real API request settles.
The deterministic production-route captures record the settled approved-poster and missing-poster detail states.

Masked comparison seed: `1707`.
The judge should inspect `masked-pair/screen-1.png`, `screen-2.png`, and `screen-3.png` before reading `masked-pair/unblind.txt`.

No production files changed in round 7.
