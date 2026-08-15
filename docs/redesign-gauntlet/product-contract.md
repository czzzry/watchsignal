# WatchSignal redesign gauntlet contract

## Outcome

WatchSignal should feel like a cinematic decision tool for two people on a couch, not a streaming catalogue or a recommender dashboard.
The attached golden result and details images set the emotional and compositional quality bar for movie-led surfaces.
The redesign must preserve every current household behavior while removing consumer-facing debug language and progressive-disclosing secondary work.

## Product invariants

- The primary viewport is a safe-area-aware 390 by 844 phone, with supported layouts from 320 to 430 pixels wide.
- Couple sessions remain setup, first private five-title pass, private handoff, second private five-title pass, and ranked result.
- Solo sessions skip the handoff and absent profile without changing ownership of saved reactions.
- Each participating person rates exactly five titles with Interested, Maybe, or No.
- Seen-before memory remains separate and never substitutes for tonight's reaction.
- Couple reactions remain private until the shared result.
- Required onboarding still collects at least one Loved, Ok, and No seed for every participating profile.
- Tonight intent remains session-only, confirmed before use, and interpreted by the language model without giving the model ownership of ranking.
- Five more excludes shown titles and carries the session's prior reactions and confirmed intent.
- WatchSignal owns ranks, scores, score gaps, explanations, interaction design, and icons.
- TMDB owns movie metadata, posters, backdrops, and cast data.
- Provider availability remains region-aware and must never imply a launch link when no provider URL exists.
- Current recommendation, language, provider, Safe Pick, and session-mode behavior stays unchanged unless separately approved.

## Surface archetypes

### Cinema stage

Reaction cards and ranked results use real movie imagery, near-black surroundings, restrained signal accents, sparse chrome, and one dominant action.
The result reference can be reproduced closely here, including the backdrop-led reveal, ranked poster strip, match score, short shared reason, and pale details sheet.

### Quiet utility

Login, setup, onboarding, intent review, details, watchlist, history, post-watch feedback, Taste Lab, and credits use calm matte surfaces and normal scrolling.
These screens inherit the same typography, spacing, controls, icons, and color system without copying the golden result's fixed-height movie backdrop composition.

### Transition chamber

Launch, handoff, shortlist generation, ballot sealing, and final matching use short focused motion with almost no controls.
Motion communicates state and never hides an artificial delay.

## Visual system

- Night 950 is `#050309`, Night 900 is `#0B0810`, Plum 850 is `#160D20`, and raised dark utility surfaces use `#141019` and `#1B1621`.
- The pale reading sheet is `#F5F2F8` with dark ink `#1C1322` and body text `#554A5A`.
- Primary dark-mode text is `#FBFAFC`, muted text is `#C3BAC8`, violet signal is `#B986FF`, and cyan signal is `#78E8F5`.
- Spacing uses only 4, 8, 12, 16, 20, 24, 32, 40, and 48 pixels.
- Screen gutters are 16 pixels below 400 pixels wide and 20 pixels from 400 to 599 pixels wide.
- Standard controls are 48 pixels high, primary actions are 54 pixels high, and all pointer targets are at least 44 by 44 pixels.
- Routine surface radii range from 12 to 16 pixels.
- Full pills are reserved for tags, progress markers, and circular controls.
- Serif typography is reserved for movie titles, handoff, launch, and the final reveal.
- Product labels, forms, controls, and body text use one clear sans-serif system.
- Production body text never falls below 12 pixels.
- Primary controls are solid near-white on dark with dark ink, with exactly one dominant action per state.
- Dynamic backdrops require a deterministic contrast scrim and may not carry essential text without passing contrast checks.
- Posters use the portrait asset and backdrops use the landscape asset.
- Missing imagery receives an intentional plum WatchSignal fallback rather than a broken image.

## Signature interactions

- A first-load signal sting resolves brief scan/static energy into the WatchSignal mark in no more than 900 milliseconds and does not replay during the same session.
- Intent crystallization turns an interpreted sentence into two to four editable signal chips along a restrained cyan-to-violet trace.
- Reaction lock-in compresses and fills the chosen response, emits one restrained signal into progress, and advances in no more than 320 milliseconds.
- Privacy seal closes the first private ballot into a neutral locked WatchSignal object before the partner handoff appears.
- Match convergence brings two participant signals into the result score arc while the winning backdrop comes into focus in no more than 850 milliseconds.
- All signature motion becomes immediate or a simple crossfade when reduced motion is requested.

## Information hierarchy

- Setup exposes People, Language, and Availability as three editable rows, a short optional Tonight entry, and one Start action.
- Reaction surfaces expose the poster, title, year, runtime, genres, one fit line, progress, three reactions, and a separate Seen before action.
- Synopsis, cast, deeper reasons, and availability details open through one deliberate Details action.
- The ranked result exposes the winner, score and gap, one shared reason, four ranked alternatives, Details, a provider action, and 5 more above the fold at the primary viewport.
- The provider action is labelled `Watch` only when a real launch destination exists.
- Without a launch destination, the provider action is labelled `Where to watch` and opens honest regional availability instructions without leaving the app.
- Long evidence, watchlist management, outcomes, history, and diagnostics do not stack beneath the reveal.
- Public errors preserve the user's selections, explain the consequence, and offer a specific recovery without naming APIs or internal infrastructure.

## Accessibility contract

- Body and control text meets 4.5 to 1 contrast and meaningful large graphics meet 3 to 1 contrast.
- Every interactive control has a visible two-pixel focus ring with a two-pixel offset.
- Details and memory overlays use real dialog semantics, trap focus, close with Escape and an explicit Close control, and return focus to the opener.
- Color never carries state alone.
- Save, retry, and progress outcomes use restrained live regions.
- The full flow supports keyboard input, 200 percent text zoom, safe areas, forced colors, reduced motion, reduced transparency, slow or missing images, and long German labels.

## Evidence gate

Every accepted slice needs a real phone-sized click-through, a 390 by 844 screenshot, functional state proof, keyboard and accessibility checks appropriate to the slice, and an independent critic's direct comparison with the golden bar.
The critic must name the largest remaining gap and reject the slice when a material gap remains.
Worker completion alone never counts as acceptance.
