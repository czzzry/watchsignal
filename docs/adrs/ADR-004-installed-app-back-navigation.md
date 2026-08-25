# ADR-004 Installed app back navigation

## Status

Accepted on 2026-08-25 by the founder for the installed WatchSignal experience.

## Context

WatchSignal's primary interface is installed from Brave as a progressive web app.
Most of the product flow uses application state rather than distinct browser pages.
The installed browser therefore treated a Back gesture as permission to leave WatchSignal, even when the user expected it to close a visible surface or return to an earlier product state.
That behavior made accidental exits common and did not provide a reliable way to step backward through Taste Lens, setup, reactions, and results.
The pass-the-phone flow also has a privacy constraint: backward navigation must never reveal another participant's sealed answers.

## Decision

WatchSignal will own Back behavior only while it is running in installed standalone mode.
The application will maintain one browser-history guard and rearm it after each Back event so repeated gestures remain inside WatchSignal.
Visible surfaces register prioritized Back handlers, with dialogs and nested views taking precedence over their containing screen.
At Home, Back is consumed and the installed app remains open.
Ordinary Brave tabs keep the browser's native Back behavior.
The pass-the-phone flow uses privacy-safe destinations.
Results and the handoff screen return to Home.
The first card in the second participant's pass returns to the handoff screen rather than revealing the first participant's ballot.
Later cards return only within the current participant's pass.
Saving and transition states consume Back until the operation reaches a safe state.

## Options considered

- Leave browser Back behavior unchanged and rely on visible buttons.
- Add a new browser-history entry for every internal state.
- Maintain one standalone-only guard and let active product surfaces declare the correct Back action.

The final option was selected because it fixes accidental exits without coupling every transient interface state to the URL or changing normal browser navigation.

## Tradeoffs

The installed app no longer uses Back as an exit shortcut while the WatchSignal Home screen is active.
Users leave through the operating system's Home or app-switching controls.
Internal Back behavior depends on each new full-screen surface or dialog registering an appropriate handler.
The guard cannot override an operating-system action that closes the entire app without sending a browser history event.

## Reversibility

Easy.
The provider, handler registrations, and pure navigation contract can be removed without changing recommendation, profile, or session data.

## Engineering evidence loop

### Claim

An installed WatchSignal session remains inside the app when the user invokes Back and moves to the nearest safe product destination.

### Contract

A standalone-only controller owns one browser-history guard.
A priority registry chooses the deepest active Back handler.
A pure wizard contract maps the current step, card index, overlay, and busy state to a privacy-safe action.

### Boundary

The standalone navigation provider owns browser history.
Individual surfaces own their local close or backward action.
Recommendation logic, profile data, saved reactions, and ordinary browser-tab navigation remain unchanged.

### Behavior

Back closes movie details, memory dialogs, result dialogs, setup panels, and Taste Lens layers before changing the underlying wizard step.
At an installed-app root, Back keeps WatchSignal open.
Backward navigation never crosses a sealed participant boundary.

### Evidence

Contract tests cover repeated Back events, unchanged browser-tab behavior, remount safety, priority ordering, and sealed-flow boundaries.
The complete repository test suite and optimized production build pass.
A phone-sized standalone browser walkthrough verified Home retention, the Taste Lens shelf-to-profile-to-directory-to-Home sequence, and setup-panel dismissal.
This evidence does not prove behavior for an operating-system gesture that terminates a web app without dispatching browser history events.

### Decision

The implementation is ready to promote after the founder authorizes publication and deployment.

## Consequences

Installed WatchSignal behaves more like a native mobile app during backward navigation.
Future full-screen surfaces and modal layers need to participate in the shared Back-handler contract.
Normal Brave browsing remains unaffected.
