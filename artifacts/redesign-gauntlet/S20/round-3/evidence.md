# S20 round 3 evidence handoff

## Claim

The separate setup Utility keeps the complete household setup through remote failure, explicit phone retention, reload, and reconnection.

## Evidence-found bounded fix

The production evidence run found that a phone-kept copy was previously restored only while disconnected.
A connected reload could therefore replace the explicitly kept setup with the remote version.

The local record is now `{ setup, pendingSync: true }`.
Every reload restores the complete pending setup regardless of connection state.
When connected, the UI says `Kept on this phone. Save to share these changes.` and offers Save setup.
A successful remote save clears the pending phone record.

## Automated evidence

- Focused S20 tests: 7 of 7 passed.
- Executable state test preserves active and partner profile IDs plus all six defaults through store, reload, edit, and keep.
- A second focused assertion proves connected hydration does not bypass the pending phone copy and that successful remote save clears it.
- TypeScript: passed.
- Diff check: passed.
- Full web suite from the round 2 UI-equivalent tree: 188 of 188 passed.
- A clean production server existed on port 3118 with a fresh build from before the evidence-found bounded fix.
- The current post-fix browser evidence used the development server, so its captures contain the Next development badge and are not claimed as clean production images.

## Real browser evidence

The deterministic pending setup contains two stable profiles and the accepted defaults.
Reload while connected produced exactly two profiles, state `local-only`, `Kept on this phone. Save to share these changes.`, and one Save setup action.

Responsive geometry:

| Viewport | Scroll width | Document height | Horizontal overflow | Save action geometry |
| --- | ---: | ---: | --- | --- |
| 320 by 844 | 320 | 1201 | No | x 16, y 1026, 288 by 54 |
| 390 by 844 | 390 | 1185 | No | x 16, y 1010, 358 by 54 |
| 430 by 844 | 430 | 1224 | No | x 20, y 1049, 390 by 54 |
| 390 by 568 | 390 | 1185 | No | x 16, y 1010, 358 by 54 |
| 195 by 844, 200-percent equivalent | 195 | 1593 | No | x 16, y 1418, 163 by 54 |

The action is reachable through normal scrolling at every size.

Keyboard order from the top was Back to WatchSignal, Profile 1 name, Profile 1 icon, Profile 1 color, Profile 2 name, Profile 2 icon, Profile 2 color, Save setup, Back to WatchSignal, Data credits.
Every setup control in that trace measured at least 44 pixels high; the global Data credits footer is 15 pixels high and remains outside this slice's control boundary.

The unsaved-leave interaction opened the exact confirmation `Leave without saving these changes?`.
The browser CLI remained in modal state before its scripted cancel and confirm trace completed, so cancel-versus-confirm navigation is not claimed as completed browser evidence.

## Captures

- `setup-pending-reconnect-390x844.png`
- `setup-320x844.png`
- `setup-390x844.png`
- `setup-430x844.png`
- `setup-390x568.png`
- `setup-200-percent-equivalent.png`

## Unproven gates

- Deterministic remote failure, Retry success, second failure, Keep on phone, then reload was not completed in the live browser before handoff.
- Reduced motion, reduced transparency, and forced colors are declared in scoped CSS but were not actively emulated this round.
- The masked pair and a post-fix clean production capture are not complete.
- The post-fix production build was not rerun because the shared server/build environment was occupied.

## Decision

Builder handoff only.
No acceptance claim.
