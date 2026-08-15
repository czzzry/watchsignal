# S21 builder evidence

## Identification

- Slice: S21 Credits and asset provenance.
- Round: One.
- Builder: Result critic reassigned as S21 builder.
- Independent critic: Pending.
- Worktree: Uncommitted gauntlet implementation on `codex/implement-cinematic-pulse`.

## Claim

Legal and data-source attribution should be clear, readable, and reachable without competing with the household movie decision.

## Contract

TMDB owns movie metadata, imagery, structured cast, and regional watch-provider availability.
WatchSignal owns ranking, Match Index, score gaps, recommendation reasons, layout, and interface icons.
The required statement that WatchSignal uses the TMDB API but is not endorsed or certified by TMDB remains exact.

## Boundary

This slice changes only the `/credits` page and its page-specific presentation.
It does not alter APIs, recommendation logic, movie data, the result screen, login, global tokens, or the household flow.

## Behavior

Direct navigation presents one calm dark Utility page with an obvious local Back to WatchSignal action.
Three concise rows distinguish movie data, provider availability, and WatchSignal-owned recommendation output.
The existing approved local TMDB logo is visible without requiring an external page or asset request.

## Evidence

- Primary capture: `credits-390x844.png`.
- Supported widths: `credits-320x844.png`, `credits-390x844.png`, and `credits-430x844.png` have no horizontal overflow.
- Short height: `credits-390x568.png` keeps the back action fixed at the top and allows normal vertical reading.
- 200 percent equivalent reflow: `credits-195x422.png` has no horizontal overflow and switches header, introduction, source rows, and footer to single-column flow.
- Text floor: page CSS contains no explicit text below 12 pixels.
- Focus: Back to WatchSignal is a native link with the shared two-pixel focus ring and two-pixel offset.
- Motion: the page introduces no page-load animation; the only transition is a 140 millisecond hover background inherited from shared tokens.
- Reduced transparency and forced colors: page-specific media rules remove translucent row backgrounds and add structural borders.
- External link risk: the credits page contains no external links, so direct navigation is not dependent on a third-party destination.
- Focused contract tests: four pass.
- Full state tests: 67 of 67 passed.
- TypeScript: passes.
- Production build: passed, including static generation of `/credits`.

## Decision

Hold for independent judgment.
The implementation and current checks support the ownership and readability claim.
They do not establish acceptance until an independent critic inspects the real output against the Utility bar.
