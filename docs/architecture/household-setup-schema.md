# Household Setup Schema

Slice 2 adds the first SQLite persistence tables for local household setup.
The schema stores only generic setup data and keeps real household names, ratings, notes, and watch history out of committed artifacts.

```mermaid
erDiagram
    households ||--o{ participant_profiles : owns
    households {
        text household_id PK
        text label
        text default_region
        text default_service
        text default_language_mode
        integer rewatch_avoidance_default
        text active_interface
        text created_at
    }
    participant_profiles {
        text profile_id PK
        text household_id FK
        text role
        text display_label
        integer sort_order
        text created_at
    }
```

The default committed setup creates one `households` row labeled `Household`.
It creates exactly two `participant_profiles` rows labeled `Husband` and `Wife`.
The SQLite path is selected through the `MOVIE_NIGHT_MEDIATOR_SQLITE_PATH` environment variable, with a local development fallback of `data/movie_night_mediator.sqlite3`.
