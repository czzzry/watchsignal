# Taste Lab Storage And API

This document describes the first private backend loop for WatchSignal Taste Lab.
It turns the signal-score queue and export contract into persistent local API behavior.

## What This Slice Adds

The backend can now:

- store Taste Lab queue candidates,
- return the next batch for one profile,
- submit a batch of Taste Lab ratings,
- persist those ratings in SQLite,
- list a profile's saved Taste Lab ratings,
- exclude importable preference ratings from later batches,
- and deprioritize `Haven't seen` movies without turning them into dislike.

This is still private infrastructure.
It is not a public user-facing Taste Lab route yet.

## Private API Shape

Seed candidates:

```http
POST /taste-lab/candidates?householdId=default-household
```

Fetch a profile queue:

```http
GET /taste-lab/{profile_id}/queue?householdId=default-household&limit=10
```

Submit ratings:

```http
POST /taste-lab/{profile_id}/ratings
```

List saved ratings:

```http
GET /taste-lab/{profile_id}/ratings?householdId=default-household
```

## Rating Behavior

`Loved`, `Liked`, `Meh`, and `Hated` are importable preference signals.
Once a profile submits one of those labels for a movie, that movie is excluded from later batches for that profile.

`Haven't seen` is familiarity-only.
It is saved so the system knows the movie was not answerable.
It is returned only after fresh unrated candidates, which keeps the queue answerable without treating unfamiliarity as negative taste.

## Data Boundaries

Taste Lab ratings remain profile-specific.
The couple-level overlap model can use those ratings later, but the raw data belongs to the individual profile that created it.

The storage contract preserves queue provenance.
That means future evaluation can compare whether high-signal candidates led to better recommendations than popularity-only candidates.

## Next Step

The next slice can build a private Taste Lab UI on top of these endpoints.
That UI should show real poster art and support fast repeated batches of 10 ratings.
