# S16 Round 7 Builder Evidence

## Claim

The Taste memory Close control remains a fully visible 44 by 44 target at narrow phone widths and 200-percent-equivalent reflow.
Contradictory genre evidence is described cautiously instead of appearing as both a positive lean and a possible avoid.

## Contract

The header uses a constrained two-column layout with a nonshrinking 44-pixel Close column.
Genres present in both positive and negative evidence maps are removed from directional lists and reported as mixed signals.

## Boundary

Only Profile memory presentation and its view-model wording changed.
Persistence, evidence collection, scoring, ranking, profile ownership, and the accepted visual direction are unchanged.

## Behavior

Real production measurements:

- 320 by 844: Close is 44 by 44 at x 260, fully inside a 320-pixel viewport; document scroll width is 320.
- 390 by 844: Close is 44 by 44 at x 330, fully inside a 390-pixel viewport; document scroll width is 390.
- 195 by 422, the 200-percent equivalent of 390 by 844: Close is 44 by 44 at x 135, fully inside the viewport; the header is 195 pixels wide and document scroll width is 195.

The populated fixture now says `Still taking shape` and `Mixed signals around Action and Adventure.` rather than presenting Adventure in both directional statements.

## Evidence

Focused Profile memory tests passed 7 of 7.
The full web state suite passed 178 of 178.
TypeScript passed.
Diff check passed.
The production build was already running in another shared process and had not completed at handoff.

## Decision

Builder handoff only.
Independent acceptance remains required.
