# S17 round 9 builder evidence

## Claim

Closing Household history with Escape returns focus to the exact `Recent nights` opener, including at the supported 200%-equivalent viewport.

## Contract

`AccessibleModal` retains its existing after-paint focus return by default and exposes an explicit synchronous return path for the Household history modal.
The Household history modal opts into that path so the invoking opener owns focus when the close cleanup completes.

## Boundary

The change is limited to focus-return timing in the shared modal and the Household history integration.
History data, list/detail presentation, navigation, and other modal behavior are unchanged.

## Behavior

Executable integration coverage verifies that the synchronous path restores focus before any animation frame callback.
Household history contract coverage verifies that its modal selects the synchronous path.

## Evidence

- Focused Household history and modal integration tests: 10/10 passed.
- Full web test suite: 191/191 passed.
- TypeScript: passed.
- Diff check: passed.
- Real 200%-equivalent browser trace: unproven.
  The in-app browser runtime reported no connected browser.
  The separate Chrome inspection connection stalled after opening the list and did not retain its attempted screenshot or return an active-element result.

## Decision

Hold for independent criticism.
The implementation and executable regression are complete, but promotion must wait for a retained real-browser trace proving exact opener identity after Escape from list and detail.
