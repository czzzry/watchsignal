# ADR-003 Private household filmmaker taste catalogue

## Status

Accepted on 2026-08-24 by the founder for personal, noncommercial household use.

## Context

The existing Taste Lens release exposed one preview filmmaker and four films, which could not deliver the intended discovery experience.
The founder requested the complete current LaCinetek filmmaker directory, the actual published selections, recognizable context for each person, search, Random, direct list browsing, and recommendation modes.
LaCinetek currently exposes 158 filmmaker profiles through its public site data.
At the time of ingestion, 156 profiles publish selections and two profiles publish no selections.
The source exposes 8,761 selection references, of which 8,748 resolve to retrievable film records and 13 remain stale source references.
The founder explicitly accepted use of this data inside the private, noncommercial household product and did not authorize a public or commercial catalogue feature.

## Decision

WatchSignal will store a generated snapshot of the complete current LaCinetek directory and its retrievable published selections in the repository.
All 158 profiles remain visible in the directory, while profiles with no published selections are clearly inactive and are never selected by Random.
Unresolved source references remain in the audit data rather than being silently discarded or invented.
The browser receives a lightweight profile directory and mapped movie anchors.
The full selection catalogue remains server-only and is returned one filmmaker at a time through a private application route.
The recommendation boundary receives only verified TMDB identifiers and fails closed when a filmmaker has no usable anchors.
Source display order is preserved as source order and is never interpreted as preference rank.
TMDB movie credits provide concise recognizable-film context, while LaCinetek remains the attributed source for the published selections and portraits.

## Options considered

- Keep a small hand-maintained preview roster.
- Fetch the full catalogue from LaCinetek during every household session.
- Store the complete snapshot in the client bundle.
- Store a generated snapshot, split the lightweight directory from the server-only full catalogue, and refresh it explicitly.

The final option was selected because it is inspectable, reproducible, fast on a phone, and does not add a runtime dependency on the source site.

## Tradeoffs

The repository grows by several megabytes because the source snapshot is checked in.
The data can become stale and therefore needs an explicit regeneration and review step.
Some published films cannot be mapped safely into the recommendation catalogue, so browse depth is greater than recommendation depth.
Private household use is enabled, but public product use remains explicitly uncleared.

## Reversibility

Easy.
The generated data, ingestion script, route, and Taste Lens directory can be removed without changing household profiles or the core recommender.

## Revisit triggers

- The product gains users outside the founder's household.
- WatchSignal becomes commercial.
- LaCinetek materially changes its site structure or published selection semantics.
- The snapshot is older than the team's accepted refresh window.
- A source begins publishing explicit preference ranks rather than display order.
- The client or deployment bundle shows a measurable performance regression.

## Engineering evidence loop

### Claim

The household can discover every current LaCinetek filmmaker, understand who they are, browse their real published choices, and use a usable list as a temporary recommendation lens.

### Contract

Each profile carries a stable curator identifier, concise movie context, portrait attribution, published and mapped counts, source provenance, and mapped TMDB anchors.
Each retrievable selection carries its source identifier, original list segment, source position, title, year, director, image, and optional mapped TMDB identifier.
Each unresolved source reference is preserved with its list segment, source position, and explicit unavailable reason.

### Boundary

The ingestion script owns source retrieval, normalization, enrichment, and audit counts.
The server route owns full-list delivery.
The lightweight directory owns discovery and recommendation anchors.
The recommender continues to own ranking and must not treat source position as preference strength.

### Behavior

Search matches filmmaker names and recognizable movie titles.
Random chooses only a filmmaker with usable mapped selections and avoids an immediate repeat.
Profiles with no source selections remain visible but inactive.
Browse shows the source list in source order.
Inspiration and exact-list modes fail closed when their required anchors are absent.

### Evidence

The catalogue integrity tests assert the 158-profile source census, the 156 active profiles, the 8,761 source references, the 8,748 retrievable selections, the 13 unresolved references, unique recommendation anchors, multi-list preservation, search behavior, and Random safety.
The complete final repository gate passed 456 API tests, 247 web tests, and the optimized Next.js production build.
A phone-sized 390 by 844 browser walkthrough opened Taste Lens, confirmed 158 directory entries, searched for Parasite, confirmed the two empty profiles were inactive, and used Random to open a usable 101-pick filmmaker.
The walkthrough opened Bong Joon-ho's 50-film shelf, navigated back, and opened Martin Scorsese's 178-film shelf with separate Formative and Alternative sections.
The walkthrough caught and verified the repair of an encoded-curator route parameter that had caused the full shelf request to return 404.
This evidence does not prove the long-term freshness of the external catalogue or recommendation quality for every filmmaker.

### Decision

Promote only after the final catalogue corrections, repeatable tests, production build, supervised code review, and live phone verification pass.
The founder owns any later decision to expand this private data boundary into a public product feature.

## Consequences

Taste Lens becomes a real household feature rather than a one-person demo.
The source snapshot and ingestion report become reviewable repository artifacts.
There is no popularity or demo fallback when a chosen lens cannot be applied.
The core household Taste Lab data model and learned recommender remain unchanged.

## Sources

- [LaCinetek About](https://www.lacinetek.com/fr-en/about)
- [LaCinetek catalogue ingestion research](../research/lacinetek-catalogue-ingestion.md)
- Founder direction in the WatchSignal implementation task on 2026-08-24
