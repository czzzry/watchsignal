# S09 Tonight defaults builder evidence

## Claim

Language, German provider availability, and the session decision rule are visible as understandable tonight defaults.

## Contract

The UI preserves existing language, availability, and `SessionMode` values and applies them only through existing callbacks.
Choices are staged locally until the single save action.
The callback returns `saved`, `local-only`, or `failed`, and all three defaults are applied atomically only for a successful or local-only outcome.

## Boundary

`TonightDefaultsSetup` owns the full-screen Tonight utility presentation and public local/save copy.
It does not own provider discovery, recommendation filtering, or persistence implementation.

## Behavior

The setup board presents one concise Tonight summary.
The utility uses readable choice rows, hides couple-only weighting for solo sessions, and avoids server-address and implementation vocabulary.
A failure keeps the sheet open, preserves all drafts, exposes Retry, and makes no board mutation.
A local-only save closes with honest phone-only language.

## Evidence

- Round-two focused S08/S09 integration and state run: 18 of 18 passing.
- Full web state suite: 112 of 112 passing.
- Web TypeScript check: passing.
- Production build: passing.
- Real isolated Chrome at 390 by 844 verifies the full dialog, staged selection, local-only save, close, and summary update.
- Clean 320, 390, 430, 390 by 568, and 200-percent-equivalent captures are stored in this directory.
- Full-app and global footer isolation uses the shared round-two modal integration proof.
- Reduced motion, reduced transparency, and forced colors were actively emulated and all three media queries reported active.

## Decision

Builder handoff only.
Acceptance belongs to the independent critic.
