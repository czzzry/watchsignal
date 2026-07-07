# MVP Plus 3 Contracts

This note defines the first shared contract surface for MVP Plus 3.
The goal is to let profile, Taste Lab, directed discovery, bookmark, explanation, and evaluation work proceed without incompatible assumptions.

MVP Plus 3 is **Directed Discovery And Real Tester Profile**.
The tracker is still in scoping until the founder accepts the issue breakdown.

## Contract Principles

- Profiles are durable local product entities with stable ids.
- Display labels are editable and must not be used as durable identity.
- `Cezary - tester` is a normal profile that can be renamed later.
- Taste Lab ratings belong to profile ids.
- The main flow should explicitly know which profiles are participating.
- Tonight-level nudges are session context unless a later approved feature promotes them to durable taste.
- LLMs may interpret user language into structured context.
- LLMs do not rank movies.
- Bookmarks are saved titles, not automatic likes.
- Five-more behavior continues the session instead of restarting it.
- Required validation should not depend on live LLM calls or private founder data.

## Profile Identity

Profile identity includes:

- `profile_id`
- `display_label`
- optional `avatar_key`
- optional `color_key`
- `created_at`
- `updated_at`

The profile id remains stable through rename.
The display label can be `Cezary - tester` during founder dogfood and something else later.

## Taste Lab Ownership

Taste Lab ratings include:

- `profile_id`
- `household_id`
- source movie identity
- title and display metadata
- rating label
- familiarity label
- queue provenance
- timestamp

Taste Lab ratings remain individual profile evidence.
Shared household recommendations may use multiple profiles, but raw ratings should not be merged into one anonymous taste bucket.

## Selected Recommendation Profiles

A recommendation session should know:

- `household_id`
- participating profile ids
- active profile order when pass-the-phone state matters
- active session nudges
- already-shown source movie ids
- session reactions
- bookmark actions

The default household can still provide two profiles.
The founder dogfood path must be able to select the tester profile as one of them.

## Directed Nudge

A directed nudge can produce:

- `confirmation_required`
- `clarification_required`
- structured filters
- soft signals
- excluded signals
- person or cast intent
- confidence
- user-facing summary

Common deterministic categories include:

- mood
- tone
- genre
- decade or year range
- runtime
- provider
- language or subtitle preference
- rewatch preference
- cast or person name

Examples:

- "scary but not bleak" maps to mood and tone signals.
- "sad but beautiful" maps to emotional signals and may ask whether the user wants to match or soften the mood.
- "90s thriller" maps to decade and genre filters.
- "nothing with subtitles tonight" maps to a language or subtitle-related constraint.
- "Jack Nicholson in it" maps to person or cast intent.

## Actor And Person Candidate Filtering

Person intent should resolve into candidate-generation constraints before scoring.
Live behavior may use TMDb person search and credits.
Required tests should use fixtures.

The scoring layer may rank the resulting candidates, but the LLM should not directly pick the final movie.

## Five-More Semantics

Five-more actions include:

- `same_direction`
- `different_direction`
- `more_like_this`
- `avoid_this`
- `add_nudge`

Every five-more action should preserve session reactions and exclude already-shown movies.
The action can preserve, remove, or replace active nudges depending on the selected intent.

## Bookmarks

Bookmark entries include:

- `household_id`
- source movie identity
- title
- optional poster and release metadata
- `saved_at`
- optional `saved_by_profile_id`
- optional seed provenance

Bookmarks are not durable taste votes.
Bookmark-as-seed can become recommendation context only through explicit user action or a separately approved scoring rule.

## Recommendation Evidence

Recommendation evidence should distinguish:

- durable profile evidence
- Taste Lab-derived evidence
- session reactions
- active nudges
- actor or person matches
- bookmarks when they are explicit context
- fallback behavior

The result view should expose enough evidence for founder dogfood without turning into raw debug output.

## Acceptance Coverage

The MVP Plus 3 acceptance gate should include:

- persistent tester profile proof
- Taste Lab rating proof
- main-flow selected-profile proof
- directed nudge proof
- actor or person nudge proof
- five-more no-repeat proof
- bookmark persistence proof
- reload or restart persistence proof
- recommendation-quality comparison
- phone-sized browser smoke

MVP Plus 3 is not done until the dogfood flow and recommendation-quality report both pass.
