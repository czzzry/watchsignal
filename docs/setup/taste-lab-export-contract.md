# Taste Lab Export Contract

This document defines the first portable rating record for WatchSignal Taste Lab.
The contract lets Taste Lab start as a private standalone calibration tool while keeping its data importable by WatchSignal later.

## Contract Goal

Taste Lab records should answer three questions without ambiguity.

- Who rated the movie?
- Which movie was rated?
- Was the answer a preference signal, a familiarity signal, or both?

The key product rule is simple.
`Haven't seen` means the person cannot rate the movie yet.
It must never be treated as dislike.

## Schema Version

The first schema version is:

```text
taste_lab.rating_export.v1
```

Every exported record includes this value so future import code can reject unsupported shapes instead of guessing.

## Required Record Shape

Each rating export includes:

- `schema_version`
- `household_id`
- `profile_id`
- `movie`
- `label`
- `familiarity`
- `preference_value`
- `watchsignal_taste_signal`
- `is_importable_preference`
- `rated_at`
- `queue_provenance`

The `movie` object includes:

- `source_movie_id`
- `title`
- `release_year`
- `tmdb_id`
- `poster_path`
- `genres`

The `queue_provenance` object includes:

- `queue_source`
- `generated_at`
- `rank`
- `signal_score`
- `score_components`

`queue_provenance` can be null for manually entered ratings.

## Label Mapping

Taste Lab supports five labels.

| Taste Lab label | Familiarity | Preference value | WatchSignal signal | Importable preference |
| --- | --- | ---: | --- | --- |
| `loved` | `seen` | `1.0` | `strong_positive` | yes |
| `liked` | `seen` | `0.65` | `positive` | yes |
| `meh` | `seen` | `0.0` | `neutral` | yes |
| `hated` | `seen` | `-1.0` | `strong_negative` | yes |
| `havent_seen` | `unseen` | null | `familiarity_only` | no |

`Meh` is real information.
It means the person saw the movie and felt neutral or weakly engaged.
It is not missing data.

`Haven't seen` is also real information.
It helps the queue avoid repeatedly asking about unfamiliar movies.
It does not become a negative taste signal.

## Example

```json
{
  "schema_version": "taste_lab.rating_export.v1",
  "household_id": "default-household",
  "profile_id": "sandy",
  "movie": {
    "source_movie_id": "movielens:1",
    "title": "Galaxy Divide",
    "release_year": 1999,
    "tmdb_id": "12345",
    "poster_path": "/poster.jpg",
    "genres": ["Sci-Fi", "Drama"]
  },
  "label": "loved",
  "familiarity": "seen",
  "preference_value": 1.0,
  "watchsignal_taste_signal": "strong_positive",
  "is_importable_preference": true,
  "rated_at": "2026-07-01T12:00:00Z",
  "queue_provenance": {
    "queue_source": "offline_signal_score_v1",
    "generated_at": "2026-07-01T11:00:00Z",
    "rank": 1,
    "signal_score": 0.91,
    "score_components": {
      "recognizability": 0.99,
      "divisiveness": 0.88
    }
  }
}
```

## Import Rules

Import should be additive.
Taste Lab ratings enrich a profile without overwriting existing couch-flow session reactions.

Import should keep each `profile_id` separate.
Couple-level overlap can be computed later, but raw Taste Lab ratings belong to the individual profile that created them.

Import should accept `is_importable_preference` records as taste evidence.
Import should store `familiarity_only` records separately so the queue can avoid repeated unfamiliar movies.

Import should preserve `queue_provenance` when present.
That lets future evaluation compare whether high-signal queue choices performed better than popularity-only choices.

## Relationship To The App

This contract does not make Taste Lab public.
It also does not change the current WatchSignal couch-flow recommender.
It creates the stable data shape that Slice 3 can persist and Slice 4 can submit from a private UI.
