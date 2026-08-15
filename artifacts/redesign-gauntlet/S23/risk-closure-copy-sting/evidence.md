# S23 ordinary-copy and launch-sting risk closure

## Claim

Ordinary household setup contains no implementation or recommendation-source diagnostics, and the first-load signal sting never delays meaningful use beyond 900 milliseconds.

## Contract

The ordinary shell does not mount the former recommendation-source strip.
The setup review renders its source row only when explicit review mode is active.
`launchStingPlan` is the single duration and replay contract: 900 milliseconds on the first normal load, no replay in the same browser session, and no animated sting when reduced motion is requested.

## Boundary

This slice changes only diagnostic presentation gating and launch-sting presentation timing.
Setup controls, recommendation selection, ranking, persistence, results, and accepted visual composition are unchanged.

## Behavior

- Ordinary mode does not render `Demo recommendations`, recommendation-testing copy, server/backend source copy, or a Backend setup row.
- Explicit review mode may render the restrained `Review source` row.
- A normal first load may show the sting for at most 900 milliseconds.
- Later loads in the same browser session skip it.
- Reduced-motion users skip the animated sting and receive no fake waiting.
- An in-memory marker preserves the no-replay behavior when session storage is unavailable.

## Evidence

- Focused S22/S23 executable tests: 7 of 7 passed.
- Full web state suite: 193 of 193 passed.
- TypeScript: passed.
- Diff check: passed.
- Production build: not rerun because the shared build process was hung and the parent explicitly directed handoff with prior build context.
- Browser capture: not repeated for this bounded source-and-timing change.

## Decision

Builder handoff only.
An independent critic owns acceptance.
