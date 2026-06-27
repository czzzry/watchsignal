# Mobile Pass-The-Phone UX Smoke

This smoke test proves that the local web app can complete the phone-sized pass-the-phone flow in a real browser.
It is intended to satisfy the repo rule that meaningful mobile UI flow changes get an actual browser click-through when practical.
On macOS it treats Brave as a first-class browser path and tries it before generic Chrome fallbacks.

## Run It

From the repo root:

```sh
pnpm smoke:ux:mobile
```

The script starts the Next.js web app on a temporary localhost port unless `MOBILE_UX_SMOKE_URL` is set.
By default it points the web app at an unused local API port so the flow uses demo data and does not write household or session data to the backend.
For browser startup it prefers, in order, `MOBILE_UX_SMOKE_BROWSER_BIN`, `BRAVE_BIN`, `CHROME_BIN`, the standard macOS Brave app path, the standard macOS Chrome and Chromium app paths, and then common PATH names such as `brave-browser` and `google-chrome`.

To target an already running local web app:

```sh
MOBILE_UX_SMOKE_URL=http://127.0.0.1:3000 pnpm smoke:ux:mobile
```

If Brave is installed in the standard macOS Applications folder, no browser override is needed.
To force a specific browser binary, provide it explicitly:

```sh
BRAVE_BIN="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" pnpm smoke:ux:mobile
```

The generic override works for either Brave or Chrome:

```sh
MOBILE_UX_SMOKE_BROWSER_BIN=/path/to/browser pnpm smoke:ux:mobile
```

`CHROME_BIN` remains supported for compatibility:

```sh
CHROME_BIN=/path/to/chrome pnpm smoke:ux:mobile
```

## What It Clicks

The smoke opens a Chromium-based browser at a 390 by 844 mobile viewport.
It clicks `Start first pass`.
It records five first-pass reactions.
It verifies the handoff screen and clicks `Start second pass`.
It records five second-pass reactions.
It verifies the results screen and reranked shortlist.
It verifies the debug history fallback message and disabled `Load` button in the default demo-safe mode.
It checks the setup, handoff, and results screens for horizontal overflow at phone width.

## Backend-Backed Debug History

The default mode intentionally avoids backend writes.
For a future isolated backend run, start the API against a temporary database and the web app against that API, then run:

```sh
MOBILE_UX_SMOKE_URL=http://127.0.0.1:3000 MOBILE_UX_SMOKE_EXPECT_API=1 pnpm smoke:ux:mobile
```

That opt-in mode clicks the debug history `Load` button and verifies persisted evidence headings.
Only use it with a test or temporary backend database.

## Expected Permission Needs For AFK Runs

No network access is required beyond localhost.
Filesystem writes are limited to the repo's normal build artifacts and a temporary browser profile under the system temp directory.
The script launches local processes for Next.js and the selected local browser.
If the backend-backed mode is used, the AFK run also needs permission to start the local FastAPI server against an isolated test database.

## Expected Output

```text
Mobile pass-the-phone UX smoke passed.
Checked URL: http://127.0.0.1:...
Browser: Brave Browser.app
Viewport: 390x844 mobile
Debug history mode: demo fallback, no backend writes
```

Any missing screen, disabled unexpected control, browser startup problem, or phone-width horizontal overflow exits non-zero.
If browser detection or startup fails, the script reports the exact candidates it checked and whether the chosen browser exited early or never exposed its DevTools endpoint.
