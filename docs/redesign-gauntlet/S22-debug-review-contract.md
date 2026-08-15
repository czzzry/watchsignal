# S22 Debug and review quarantine

## Claim

Ordinary household use neither renders nor requests raw recommendation evidence or review notes.
Explicit `?review=1` keeps the existing review tools available.

## Contract

Only the exact `review=1` query enables diagnostic behavior.
The same review-mode value gates diagnostic rendering, the initial debug-history request, taste-profile evidence requests, and diagnostic refreshes after watchlist or outcome mutations.

## Boundary

The pass-the-phone review integration owns this gate.
Public household history, recommendation behavior, persistence semantics, and accepted result presentation remain unchanged.

## Behavior

Ordinary mode exits diagnostic loaders before any request can start and skips all lifecycle or persistence refreshes.
Review mode retains the existing evidence panels, review notes, loading behavior, and retry behavior.
There is no review-mode entry link in the household interface.

## Evidence gate

Focused tests must prove exact query parsing and every fetch trigger.
An independent browser run must prove zero debug-history requests and no diagnostic UI in ordinary mode, then prove visible diagnostic UI and allowed requests with `?review=1`.
