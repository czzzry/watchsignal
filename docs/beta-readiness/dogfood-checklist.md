# Dogfood Checklist

Dogfooding means using WatchSignal like the first real local user would use it.

It is not only a test command.

It checks whether the product still feels understandable, pass-the-phone friendly, and trustworthy after engineering changes.

## Automated Dogfood Smoke

Run:

```sh
pnpm beta:dogfood
```

Expected result:

```text
Mobile pass-the-phone UX smoke passed.
Viewport: 390x844 mobile
Debug history mode: backend-backed load
Outcome mode: watched_recommended best pick
```

## Manual Dogfood Path

Start the backend and web app from the fresh checkout runbook.

Open the app on a phone-sized viewport.

Confirm the setup screen explains the two profiles and defaults clearly enough to start.

Start the first pass.

React to all five movies as the first person.

Pass to the second person.

React to all five movies as the second person.

Review the final pick and backups.

Save the best pick to the shared watchlist.

Mark the saved title watched.

Remove it from the shared watchlist.

Save the session outcome.

Save one feedback rating for each profile.

Start a new night.

Open recent nights.

Load the latest session.

Confirm the detail view shows outcome, feedback, founder reactions, and recommendation evidence.

## What To Notice

The screen should not require developer knowledge.

The result should explain why the winner is reasonable.

The watchlist and watched actions should feel reversible and legible.

The history view should reassure the user that the night was saved.

Any failure should say what went wrong in visible UI, not only in the browser console.

## Stop Conditions

Stop and file a Beta Readiness issue if the app cannot be started from the runbook.

Stop and file a product issue if the winning recommendation feels impossible to trust.

Stop and file a UX issue if a phone-sized screen hides or overlaps a primary action.

Stop and file an API issue if outcome, feedback, history, or debug evidence fails to persist.
