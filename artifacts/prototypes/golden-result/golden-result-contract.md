# WatchSignal Golden Result Contract

## Purpose

This artifact is the proposed visual and interaction target for the full-result-screen redesign gauntlet.
It is a prototype reference, not production code and not an approval decision.

## Required behavior

- The first view communicates the winning movie, its score, the score gap, the short reason, and the other four ranked scores without scrolling.
- Tapping `Details` or the movie title opens the expanded movie-information state in one action.
- The expanded state includes a synopsis, top cast, score evidence, and German watch availability.
- Tapping a poster in the ranked filmstrip changes the active movie without losing the other four scores.
- `5 more` preserves the path to the refinement flow.
- The result screen never presents every score as near-certain.

## Data source map

| Visible element | Owner | Current production contract | Golden-target requirement |
| --- | --- | --- | --- |
| Title, year, runtime, genres | TMDB movie details | Supported | Unchanged |
| Portrait poster | TMDB `poster_path` through `posterUrl` | Supported | Unchanged |
| Wide cinematic background | TMDB movie-images response or default `backdrop_path` | Not exposed | Add `backdropUrl` plus a deterministic selection policy |
| Synopsis | TMDB `overview` | Supported | Unchanged |
| Cast names | TMDB appended `credits.cast` through `topCast` | Supported as names | Unchanged for names |
| Cast character and headshot | TMDB `credits.cast.character` and `profile_path` | Not exposed | Enrich the cast display contract or omit headshots |
| Provider and access type | TMDB `watch/providers`, region `DE` | Supported | Render the access type explicitly |
| Rank, score, score gap, and explanation | WatchSignal recommender | Supported in ranked results and scoring evidence | Never source from TMDB |
| Buttons and interface icons | WatchSignal UI | App-owned | Use local SVG or an approved icon package, never the movie API |

## Golden-image inputs

The selected Arrival backdrop is `https://image.tmdb.org/t/p/original/hNCqkXbWd40eftqSdjq8TmV7Mqr.jpg` from the TMDB `/movie/329865/images` response.
The Arrival poster is `https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg`.
Cast headshots in the expanded state use TMDB profile images.
The prototype's synopsis, cast, genres, runtime, and provider labels were checked against the configured TMDB API on 2026-08-12.
The currently configured live adapter calls `/movie/{id}?append_to_response=credits,watch/providers`; it does not call the images endpoint or expose a backdrop URL yet.

## Gauntlet acceptance bar

- The implementation matches the approved golden screenshot at a 390-by-844 CSS-pixel phone viewport, excluding operating-system chrome.
- All primary text reaches WCAG AA contrast.
- The screen contains exactly one visually dominant action.
- Details, Watch, and 5 more are visible without scrolling.
- The details state opens in one tap and closes by the close button or backdrop tap.
- The main screen never shows more than the short recommendation reason.
- The expanded state contains the synopsis and three cast members without another navigation step.
- Poster and backdrop roles remain distinct.
- Missing remote imagery has a deliberate fallback in production implementation.
- Reduced-motion users receive an immediate state transition.

## Source and licensing note

The existing product credits page states that movie metadata and images are supplied by TMDB and that the product is not endorsed or certified by TMDB.
Production implementation must preserve the required TMDB attribution and re-check provider-display requirements before release.
