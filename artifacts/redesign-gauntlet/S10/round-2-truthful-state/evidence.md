# S10 truthful onboarding state round 2 builder handoff

## Claim

Connected onboarding never presents an unresolved completion check as a save or a known zero-of-N result.

## Contract and boundary

`onboarding-truthful-state.ts` owns the public completion and saving state behind injected completion-read and profile-save ports.
The production onboarding hook subscribes to this controller, and the production setup screen uses the same presentation function exercised by the integration tests.

## Behavior

- A delayed initial completion read renders `Checking` and `Checking taste setup`, with no `Saving` or `0 of N`, and keeps Start disabled.
- A resolved unlocked completion enables `Start first pass`.
- A pending profile save after known completion renders `Saving` while retaining the last known count.
- A rejected or aborted completion read renders `Couldn’t load taste setup. Your current setup is unchanged. Try again.` with no false completion.
- A connected first render begins in checking state before the effect runs.
- Stale completion reads receive and honor a real abort signal.

## Evidence

- The executable integration suite failed first because the production-used controller seam did not exist.
- Focused onboarding, public-error, and release-boundary tests passed: 23 of 23.
- TypeScript passed with no output.
- Scoped diff checking passed.
- Full web and production build were not rerun by this builder before handoff.

## Decision

Hand off for independent criticism.
No acceptance claim is made.
