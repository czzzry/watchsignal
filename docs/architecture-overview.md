# Architecture Overview

This document is the visual companion to the founder decisions and workflow map.
It is intentionally high-level.
It should evolve as the real system evolves.

## System context

```mermaid
flowchart LR
    A["Founder on phone browser"] --> B["Next.js mobile web app"]
    C["Pass-the-phone participant"] --> B
    B --> D["FastAPI backend"]
    D --> E["SQLite operating store"]
    D --> F["Scoring module"]
    D --> G["TMDb metadata and provider data"]
    F --> E
    D --> H["Future LLM interpretation module"]
```

## First vertical slice flow

```mermaid
flowchart TD
    A["Open local mobile web app"] --> B["Confirm household profiles"]
    B --> C["Start shared movie night"]
    C --> D["Show default mode and allow override"]
    D --> E["Apply remembered defaults"]
    E --> F["Ask only minimum clarifying questions"]
    F --> G["Fetch candidates from TMDb"]
    G --> H["Apply Safe Pick gate"]
    H --> I["Score via separate module"]
    I --> J["Show five-title shortlist"]
    J --> K["Founder reacts"]
    K --> L["Hand phone over"]
    L --> M["Wife reacts"]
    M --> N["Rerank shortlist"]
    N --> O["Show best pick and reranked shortlist"]
    O --> P["Later record what was watched"]
    P --> Q["Collect Loved or Fine or No"]
    Q --> R["Update history, metrics, and taste signals"]
```

## Shared-session input modes

```mermaid
flowchart TD
    A["Shared session"] --> B["Separate-device mode"]
    A --> C["Pass-the-phone mode"]
    C --> D["MVP primary"]
    B --> E["MVP plus N"]
    E --> F["Each person scores on own phone"]
    D --> G["One person scores, then hands off phone"]
    F --> H["Same session artifacts and recommendation logic"]
    G --> H
```

## Responsibility split

```mermaid
flowchart LR
    A["Next.js mobile UI"] --> B["FastAPI API layer"]
    B --> C["Application use cases"]
    C --> D["Scoring module"]
    C --> E["SQLite persistence"]
    C --> F["TMDb adapter"]
    C --> G["Future LLM interpretation adapter"]
    E --> H["History, metrics, watched state, feedback"]
```

## Recommendation application boundary

The API route validates and translates HTTP payloads but does not execute the recommendation workflow.
`RecommendationService` owns profile and memory evidence loading, candidate-source selection, fetch budgeting, scorer selection, shortlist generation, snapshot creation, and application-level failure semantics.
The TMDb adapter owns provider communication and candidate construction.
The scoring module owns ranking policy and evidence generation.

```mermaid
flowchart LR
    A["Recommendation HTTP route"] --> B["Typed RecommendationRequest"]
    B --> C["RecommendationService"]
    C --> D["Profile and memory evidence"]
    C --> E["Candidate source"]
    C --> F["Scoring module"]
    C --> G["Recommendation snapshot"]
    E --> H["TMDb adapter or demo fixtures"]
```

The live candidate pipeline has one execution path for fetching, exclusion, enrichment, watched-state marking, scoring, and snapshotting.
Callers may request ranked domain candidates or display-ready shortlist items without duplicating that pipeline.

## Pass-the-phone state boundaries

The pass-the-phone UI uses pure reducers for flow state and wizard navigation.
Session synchronization, tonight-intent interpretation, results evidence, history panels, and navigation advance through named transitions.
Application-level session operations own shortlist loading, shared-session creation, fallback recovery, continuation scoring, reaction persistence, seen-memory persistence, and handoff advancement.
Those operations receive explicit state snapshots and output ports, so they can be tested without rendering React components.
Focused hooks own asynchronous UI concerns for tonight-intent interpretation, session history, and results persistence.
Components render the resulting state and do not directly choose arbitrary synchronization or wizard states.
The main wizard is the composition layer that connects reducers, application operations, hooks, and screen components.
Review-only evidence fixtures live outside the production orchestration component.

```mermaid
flowchart LR
    A["User action"] --> B["Focused hook or session operation"]
    B --> C["Explicit output port"]
    C --> D["Named reducer action"]
    D --> E["Pure state transition"]
    E --> F["Rendered phone UI"]
```

The results screen delegates outcome capture, watchlist behavior, watched-state recording, and post-watch feedback persistence to a dedicated results controller.
The results component is responsible for composing panels and presentation, while the controller owns backend mutations and their local loading, error, and saved states.

## Upgrade path

```mermaid
flowchart TD
    A["MVP"] --> B["MVP plus 1"]
    B --> C["MVP plus N"]
    A1["Local mobile web flow"] --> A
    A2["TMDb + SQLite"] --> A
    A3["Simple modular scoring"] --> A
    A4["Structured feedback loop"] --> A
    B1["LLM-assisted feedback interpretation"] --> B
    B2["Stronger scoring experiments"] --> B
    B3["Possible storage upgrade path"] --> B
    C1["Taste profile snapshot"] --> C
    C2["Ideal movie synthesis"] --> C
    C3["Known-show episode recommender"] --> C
```

## Constraint model

```mermaid
flowchart TD
    A["Household defaults"] --> D["Session setup"]
    B["Individual taste profiles"] --> D
    C["Session overrides"] --> D
    A1["Prime Germany usually on"] --> A
    A2["English audio or foreign plus English subtitles"] --> A
    A3["Rewatch avoidance"] --> A
    B1["Personal taste signals"] --> B
    B2["Per-person watched history"] --> B
    C1["Tonight's service"] --> C
    C2["Tonight's mode"] --> C
    C3["Tonight's runtime"] --> C
```
