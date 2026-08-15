# S20 round 4 production recovery evidence

## Claim

The separate setup Utility keeps the complete household setup through save failure, retry, explicit phone retention, reload, and reconnection without silently reverting profile or default state.

## Contract

The component owns one complete `SetupState`.
Its phone record is `{ setup, pendingSync: true }`.
A remote save is allowed to clear that record only after the full setup is accepted.
A failed save must retain every draft value and expose Retry plus Keep on this phone.

## Boundary

This evidence covers the separate `/setup` Utility and its local persistence seam.
It does not change the setup API schema, the main recommendation flow, or the accepted S08 and S09 setup sheets.

## Production build

The current tree completed a clean optimized Next production build.
Compilation, TypeScript, page-data collection, and all 33 static pages completed successfully.
The tested production server ran the current build on port 3120 against a dedicated current API on port 8020.

## Real production interaction

The following sequence was completed in the actual production route.

1. Profile 1 was changed to `Cezary Recovery Test`.
2. The API was stopped and Save setup was activated.
3. The page remained on `/setup`, retained the edited profile, displayed `Couldn’t save. Your changes are still here.`, and exposed Keep on this phone plus Try again.
4. The API was restarted and Try again was activated.
5. The page displayed `Saved for your household.` and disabled the action as Saved.
6. Profile 2 was changed to `Sophie Local Pending`.
7. The API was stopped and Save setup was activated again.
8. The second failure retained both edited profiles and again exposed Keep on this phone plus Try again.
9. Keep on this phone was activated.
10. The page displayed `Kept on this phone.` and kept the complete six-profile setup plus all defaults.
11. The API was restarted and `/setup` was reloaded while connected.
12. The page restored both edited profile names, preserved all six profiles and every defaults-review value, displayed `Kept on this phone. Save to share these changes.`, and offered Save setup.

The connected reload did not replace the explicitly retained phone copy with the older server copy.

## State observed after reconnect

- Profile 1: `Cezary Recovery Test`
- Profile 2: `Sophie Local Pending`
- Six profiles present
- Watching: `Cezary Recovery Test + Husband`
- Language: `English audio or verified English subtitles`
- Available on: `Any streaming Germany`
- How it works: `Movie night · Pass the phone`
- Shortlist: `5 movies · Watched titles hidden`
- Status: `Kept on this phone. Save to share these changes.`
- Dominant action: `Save setup`

## Existing responsive and accessibility evidence

The production CSS did not change after round 3.
The existing current-code responsive evidence remains applicable: 320, 390, 430, 390 by 568, and 195-pixel 200-percent-equivalent widths had no horizontal overflow, the Save action remained reachable and 54 pixels tall, and setup controls measured at least 44 pixels.
The keyboard order remained logical.
The global footer target was subsequently corrected in the accepted S23 risk closure.

## Validation

- Focused S20 tests: 7 of 7 passed again after the production interaction.
- Full web suite: 192 of 192 passed on the current tree before the later additive S23 risk-closure tests.
- TypeScript: passed.
- Current optimized production build: passed, 33 of 33 pages generated.
- Real failure, retained draft, Retry success, second failure, Keep on phone, connected reload, and complete pending-state restoration: passed.

## Evidence limitations

The browser connection ended after the recovery sequence, before the native unsaved-leave dialog could be completed in both Cancel and Confirm directions.
Round 3 already proved that the exact `Leave without saving these changes?` dialog appears.
Fresh active reduced-motion, reduced-transparency, and forced-colors browser traces were not repeated in round 4; the scoped contracts and current source remain unchanged.
No round-4 screenshot was saved before the browser disconnected, so the round-3 responsive captures remain the visual evidence while this document records the real production recovery trace.

## Decision

Independent critic verdict: ACCEPT, 33 of 40.

- Visual hierarchy and emotional quality: 4
- Golden-system fidelity: 4
- Task clarity and word economy: 4
- Cross-surface coherence: 4
- Functional fidelity: 5
- Mobile composition: 4
- Accessibility and resilience: 4
- Overall finish: 4

The critic found the retained Utility comparison equivalent in quality to the accepted S09 reference.
The missing fresh Cancel and Confirm captures were classified as non-material because the exact branch is deterministic and tested, while the responsive and accessibility styling remained unchanged from prior evidence.
No hard reject remains.
