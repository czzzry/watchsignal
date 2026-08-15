# S02 round 1 evidence record

## Identification

- Slice: S02 Golden ranked result and Match Index v1.
- Round: One.
- Builder: Result builder.
- Independent critic: Result critic.
- Worktree: Uncommitted gauntlet implementation on `codex/implement-cinematic-pulse`.

## Claim

The real production result should match the golden cinematic hierarchy while preserving all five ranked alternatives and every existing result action.
Its match number should be an honest index rather than a probability or a forced rank gap.

## Contract

`RankedCandidate` carries a versioned `MatchIndexBreakdown` with an unclamped combined raw value, a fixed complete-domain affine transform, an unrounded exact index, and one rounded household display index.
`RankedResultStage` owns active-movie presentation and progressive-disclosure entry points without changing recommendation order or persistence behavior.

## Boundary

This slice owns the production ranked-result main state, Match Index presentation, ranked-title switching, and entry points to Details, provider information, five more, and existing result utilities.
It does not change recommender weights, API ordering, provider availability facts, the full S03 details sheet, or later utility-surface designs.

## Expected behavior

The primary phone viewport shows the active movie, match index, exact lead language, one shared reason, five total scores, Details, a truthful provider action, and 5 more without scrolling.
Switching an alternative changes its image, title, metadata, reason, score, rank language, and provider state without losing the other four titles.
Existing watchlist, outcome, post-watch, new-night, and review evidence remain reachable through progressive disclosure.

## Canonical fixture

- Viewport: 390 by 844 CSS pixels.
- Household: Husband and Wife in compromise mode.
- Availability: Prime Video Germany.
- Ballot: Both participants mark all five deterministic demo titles Interested for the primary screenshot.
- Active movie: Arrival.
- Network: Local demo mode with an honest unavailable-session message in continuation and persistence actions.
- Images: Verified TMDB Arrival poster and backdrop with intentional WatchSignal fallback for missing unverified remote imagery.
- Motion: Default for the main capture, with a separate reduced-motion check.

## Required interactions

| Action | Expected result | Observed result | Pass |
| --- | --- | --- | --- |
| Complete first five-title pass | Private handoff appears without showing votes | Handoff appeared after the fifth reaction | Yes |
| Complete second five-title pass | Result appears only after the full ballot | Result appeared after all ten reactions | Yes |
| Select every ranked poster | Active movie content changes and five-title context remains | Verified for all five titles | Yes |
| Open Details | One-action details entry opens for the active movie | Verified | Yes |
| Close Details with Escape | Sheet closes and focus returns to its trigger | Verified | Yes |
| Open provider action without a URL | Honest regional availability appears without false navigation | `Where to watch` opened an informational state | Yes |
| Open 5 more | Existing continuation and steering flow remains reachable | Dark continuation sheet opened | Yes |
| Open result options | Watchlist, outcome, post-watch, and new-night functionality remains reachable | Dark result utility sheet opened | Yes |
| Enter explicit review mode | Internal evidence is visible only for evaluators | Verified separately from ordinary household mode | Yes |

## Pre-judge evidence

- Candidate screenshot: `ranked-result-390x844.png`.
- Five-more state: `five-more-dark.png`.
- Result utility state: `result-options-dark.png`.
- Comparison screenshot: `../../prototypes/golden-result/golden-result-main.png`.
- Masking and random assignment: To be appended by the independent critic before its visual verdict.
- Width checks: 320, 390, and 430 pixels had no horizontal overflow and retained a reachable dock.
- Keyboard: Primary controls were reachable and details Escape behavior passed.
- Focus return: Details returned focus to the opening control.
- Reduced motion: Shared global and result-stage motion collapses to one millisecond.
- Missing image: Result stage renders deterministic WatchSignal fallback art when a backdrop is absent or fails.
- Offline and local mode: Provider, continuation, and persistence states remain honest and do not claim an unavailable launch or save.
- Tests: 38 of 38 state and Match Index tests passed.
- Build: TypeScript and production build passed.

## Decision before independent judgment

Hold.
The builder and helm checks prove the bounded behavior works in the tested local flow.
They do not prove that the candidate matches the golden quality bar or passes the full independent accessibility and resilience audit.
