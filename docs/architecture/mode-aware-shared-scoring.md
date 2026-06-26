# Mode-Aware Shared Scoring

Issue 7 adds the first backend scoring behavior for shared couple sessions.
The scorer still remains a replaceable heuristic module, not a permanent recommendation formula.

## Inputs

Shared scoring receives a session context, household defaults, two participant profiles, and candidate metadata.
Candidate metadata now includes a `safety_status` value from the Safe Pick boundary and an `is_interesting_safe_pick` marker.
The scorer does not decide whether a title is watchable.
It consumes that classification and ranks only `safe_pick` candidates for shared-session main recommendations.

## Outputs

Each ranked candidate includes per-person scores, a group score, a concise reason, hard-filter status, and an interesting-pick marker.
The recommendation result also exposes `interesting_safe_pick` when at least one ranked Safe Pick is marked interesting.
This gives later API and UI slices a direct way to reserve one interesting-but-safe option without making the scorer own UI layout.

## Session Modes

`husband_first` favors the first participant's score while still keeping the second participant in the calculation.
`wife_first` does the inverse.
`compromise` uses a least-misery shape so a strong dislike can pull down an otherwise one-sided favorite.
The current weights are intentionally test-covered only through observable ordering, because they are expected to change as real feedback arrives.

## Tradeoffs

The current scorer uses onboarding seed genres as lightweight preference signals.
That is enough to show mode-aware behavior but not enough to claim deep taste understanding.
The Safe Pick gate and any future TMDb availability correction logic stay outside the scoring module.
The scorer's job is to combine already-classified candidates with visible per-person taste signals and session mode.
