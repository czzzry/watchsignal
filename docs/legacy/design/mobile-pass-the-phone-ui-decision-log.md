# Mobile Pass-the-Phone UI Decision Log

## Purpose

This log captures founder decisions made while reviewing the UX/UI discovery brief.
It is intentionally lightweight.
It is not an implementation plan.

## Status Key

- `Approved`
- `Rejected`
- `Open`

## Decisions

### 1. Separate first-time welcome from returning-night startup

Status.
`Approved`

Decision.
Yes.

Notes.
Startup should change based on user state.
Keep room for a future solo-watcher variant.

### 2. Hide `Recent nights` by default on the startup screen

Status.
`Approved`

Decision.
Yes.

Notes.
Keep the feature, but do not surface it in the main startup view by default.
Access pattern still needs a separate decision.

### 3. Remove API and debug language from the normal user path

Status.
`Approved`

Decision.
Yes.

Notes.
Diagnostics and backend language should move out of the normal couple flow.

### 4. Treat `session mode` as an advanced setting instead of a front-stage choice

Status.
`Approved`

Decision.
Yes.

Notes.
This is the control that nudges recommendations toward husband-first, wife-first, or compromise for a given night.
Keep it off the main startup path.
This feature can be reconsidered or cut later if it does not prove useful.

### 5. Keep onboarding as a modal versus turning it into a full-screen mini-flow

Status.
`Approved`

Decision.
Full-screen mini-flow.

Notes.
Founder approved moving onboarding into a dedicated, focused first-use flow.

### 6. Add a compact `More details` expansion on each reaction card

Status.
`Approved`

Decision.
Yes.

Notes.
Keep the main reaction card fast, but allow optional deeper detail.
This becomes more valuable once richer recommendation explanations exist, including future LLM-assisted explanations.

### 7. Move post-watch outcome capture out of the immediate results moment

Status.
`Approved`

Decision.
Yes.

Notes.
Capture the actual outcome later, not in the immediate post-pick moment.

### 8. Keep the persistent review-note widget visible in normal founder testing mode

Status.
`Rejected`

Decision.
No.

Notes.
Hide this in normal founder testing mode.
Bring it back through a deliberate review or testing surface when needed.

### 9. Use a hybrid visual lane with `Premium Cinema Utility` as the base and `Soft Neon Night` as the accent system

Status.
`Approved`

Decision.
Yes, with refinement notes.

Notes.
Founder prefers the hybrid direction over the calmer base-only direction.
Follow-up refinement is still needed for font choice, control language, button and toggle shape, and the progress/status treatment.
Replace the current five-circle-style progress feel with a more elegant progress solution, potentially a single status bar.
