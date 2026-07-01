# Taste Lab Recommendation Evaluation

This document describes the first local evaluation harness for Taste Lab.
It compares recommendation behavior before and after different Taste Lab seeding strategies.

## Purpose

The goal is not to claim that the recommender is solved.
The goal is to create a repeatable check before changing production ranking behavior.

The first fixture compares:

- `no_taste_lab`: no Taste Lab ratings,
- `popularity_seeded`: broad popular seed ratings that are not targeted to shared boundaries,
- `high_signal_seeded`: ratings selected to reveal shared positive taste and one-sided negative boundaries.

## Run The Evaluation

From the repo root:

```sh
python3 scripts/taste_lab_evaluation.py
```

The command prints JSON with:

- ranked rows for each strategy,
- the target shared-fit movie rank,
- top pick per strategy,
- and rank delta versus the no-taste baseline.

Positive rank deltas mean the target movie moved closer to rank 1.

## Current Limitation

The current production heuristic scorer only understands three seed labels: `loved`, `fine`, and `no`.
The evaluation adapter maps Taste Lab labels into those buckets:

- `Loved` becomes `loved`,
- `Liked` becomes `fine`,
- `Meh` becomes `fine`,
- `Hated` becomes `no`,
- `Haven't seen` is ignored as preference evidence.

This is intentionally conservative.
It lets Taste Lab data pass through the existing scorer without changing production ranking behavior.
A later scorer should learn from the richer five-label contract directly.

## How To Read This

If high-signal seeding improves the fixture target rank, that is only a smoke signal.
It proves the evaluation loop can detect ranking movement.
It does not prove the real recommender is better for real users.

The next stronger version should use held-out MovieLens users or a larger fixed scenario set.
