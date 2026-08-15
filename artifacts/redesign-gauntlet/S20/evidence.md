# S20 separate setup Utility evidence handoff

## Claim

A household can edit its profiles, review the existing defaults, and save from `/setup` without technical vocabulary or silent loss.

## Contract

The complete existing `SetupState` remains the save and local-retention payload.
Presentation status is explicit as `clean`, `unsaved`, `saving`, `saved`, `failed`, or `local-only`.
A failed remote save leaves the current profile drafts unchanged.

## Boundary

This slice changes only the separate setup route, its wizard, its scoped styles, and focused S20 tests.
The API schema and in-flow S08 and S09 mappings are unchanged.

## Behavior

- The household sees editable profile names, icons, and colors in one compact section.
- The existing language, availability, session, input, shortlist, and watched-title defaults are shown in a read-only review.
- Save setup is the only dominant action.
- A remote failure offers Try again and Keep on this phone without discarding the draft.
- Offline setup says that changes can stay on this phone and stores the complete setup locally only after explicit confirmation.
- Leaving with an unsaved draft requires confirmation.
- Back to WatchSignal remains available.

## Round 2 automated evidence

- Focused S20 tests: 6 of 6 passed.
- The executable local-state regression stores, reloads, edits, and keeps a complete setup while preserving stable profile IDs, active and partner pairing, and all six defaults.
- Full web state suite: 188 of 188 passed.
- TypeScript: passed.
- Diff check: passed.
- Production build: not rerun because a competing shared build remained hung at zero CPU; the parent explicitly directed handoff with prior build context.

## Round 2 browser evidence

The browser became available through the project browser-test route after the original handoff.
The real `/setup` route loaded a deterministic two-profile disconnected state.
The accessibility snapshot measured every interactive control at 44 pixels or taller, showed all six default values through the review, showed no technical vocabulary, and exposed one honest `Keep on this phone` action.
The 390 by 844 capture has no horizontal overflow and is stored under `round-2/`.
The shared route is a development server and includes its development badge, so it is not a clean production visual artifact.
The remaining 320, 430, short-height, 200-percent, keyboard, unsaved-leave, induced failed Retry/local completion, reduced-mode, clean production, and masked A/B gates remain for the independent critic or an evidence-only round.

## Decision

Builder handoff only.
No acceptance claim.
