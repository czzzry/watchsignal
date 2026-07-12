# Taste Signal Scale Contract

Date: 2026-07-12.
Status: Active contract note.

## Purpose

WatchSignal uses several rating scales because different moments need different friction levels.
That is acceptable only if every scale has an explicit mapping into the canonical internal taste signal.

The canonical internal taste value is `preference_value`.
It ranges from `-1.0` to `1.0`.
`None` means the event is not taste preference evidence.

## Canonical Scale

| Meaning | Canonical value | Notes |
| --- | ---: | --- |
| Strong positive | `1.0` | Strong evidence the person likes this kind of movie |
| Positive | `0.65` | Useful positive evidence, weaker than loved |
| Neutral | `0.0` | Known but not positive enough to become a like |
| Strong negative | `-1.0` | Strong evidence the person rejects this kind of movie |
| Familiarity only | `None` | Not taste evidence |

## Source Scales

| Source | Labels | Mapping |
| --- | --- | --- |
| Taste Lab | Loved, Liked, Meh, Hated, Haven't seen | Loved `1.0`, Liked `0.65`, Meh `0.0`, Hated `-1.0`, Haven't seen `None` |
| MovieLens | 0.5 to 5.0 stars | `(rating - 3.0) / 2.0`, clamped to `-1.0..1.0` |
| Learned model fold-in | Canonical `preference_value` to MovieLens-like rating | `3.0 + 2.0 * preference_value`, clamped to `0.5..5.0` |
| Post-watch feedback and manual backfill | Loved, Fine, No | Loved is positive, Fine is soft positive, No is negative |
| Shortlist reactions | Interested, Maybe, No, Seen | Tonight-level session intent, not durable taste by itself |

## Lossy Adapters

The old three-bucket onboarding seed shape supports only `loved`, `fine`, and `no`.
It has no neutral bucket.
When Taste Lab ratings are adapted into that shape for fixture evaluation, the adapter must not turn `Meh` into `fine`.
`Meh` is neutral evidence in the canonical contract, so the lossy three-bucket adapter skips it.

This keeps `Liked` distinct from `Meh`.
`Liked` can become `fine` when the destination has no separate liked bucket.
`Meh` must remain neutral or be excluded from that destination.

## Product Rule

`Haven't seen` is never dislike.
It is familiarity-only evidence.

`Meh` is not missing data.
It is a known neutral preference.
If a downstream system cannot represent neutral preference, it should skip `Meh` and preserve the original Taste Lab row for richer systems.

## UX Rule

The UI should not ask ordinary household users for numeric ratings when a simpler choice captures the needed intent.
MovieLens shows that finer-grained historical ratings are useful for offline model training, but that does not mean WatchSignal should make movie night feel like data entry.

The product should collect low-friction labels and preserve richer meaning internally.
For example, Taste Lab can ask `Loved`, `Liked`, `Meh`, `Hated`, or `Haven't seen`, then store `1.0`, `0.65`, `0.0`, `-1.0`, or `None`.
The couch flow can stay even lighter with `Interested`, `Maybe`, `No`, and `Seen` because those reactions describe tonight's shortlist, not permanent taste identity.

When the model needs finer data, the right move is usually to infer strength from repeated simple signals, watch outcomes, and consistency over time.
It is not to force a person to rate a movie out of 10.

## Evaluation Rule

MovieLens evaluation thresholds are separate from product labels.
For ranking evaluation, ratings `>= 4.0` are treated as positive and ratings `<= 2.5` are treated as negative.
The values between them are neutral for ranking evaluation.

That thresholding is for measuring models, not for rewriting user profile evidence.
