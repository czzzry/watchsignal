# Sophie Household Validation Status

Date: 2026-07-12.
Status: Profile collected, household validation deferred.

## Decision

Sophie's Taste Lab profile is ready for a first household calibration pass, but WatchSignal has not yet validated couple-mode recommendation quality with real Cezary and Sophie usage.
The household gate remains pending until the app is used in a real movie-night context next week.

This closes the current Sophie setup slice as evidence collection, not as a product-promotion result.
The product default remains unchanged.
The offline individual-taste champion remains the regularization-2.0 collaborative model.
V2 remains the deployed product default until a separate household decision changes it.

## Evidence Collected

The active app database contains `80` Taste Lab rows for `sophie-tester`.
Of those rows, `34` are importable taste preferences and `46` are `Haven't seen` familiarity rows.

Sophie preference labels:

| Label | Count | Meaning |
| --- | ---: | --- |
| Loved | 7 | Strong positive taste evidence |
| Liked | 21 | Positive taste evidence |
| Meh | 5 | Neutral or weakly negative taste evidence |
| Hated | 1 | Strong negative taste evidence |
| Haven't seen | 46 | Familiarity-only evidence, not dislike |

The Taste Lab import also created `34` active `taste_lab_rating` memory events for `sophie-tester`.
The `46` familiarity-only rows are stored as too weak for taste scoring.

## Boundary

This evidence proves that Sophie's calibration data was saved and imported into profile memory.
It does not prove that the recommender works better for the household.
It does not prove that collaborative or hybrid should become the product default.
It does not prove that the couple compromise layer handles real Cezary and Sophie tradeoffs well.

The active household setup was still `cezary-tester` plus `profile-1` when this status was recorded.
That means Sophie's profile exists, but it should not be treated as the active partner in normal couple mode until setup state is deliberately changed or the UI selects that pair.

## Deferred Household Gate

The next real household validation should happen after release, when Cezary and Sophie use the app naturally.
That run should capture the shortlist, each person's reactions, the final chosen movie, and post-watch satisfaction.

The household validation question is:

Does the app produce recommendations that feel fair and usable for both real people when individual taste evidence, tonight intent, availability, and compromise logic interact?

## Engineering Evidence Loop

Claim: Sophie profile evidence is available for future household validation.

Contract: `taste_lab_ratings` preserves raw labels, familiarity, preference value, profile identity, and provenance.
`taste_memory_events` exposes importable Taste Lab evidence to scoring.

Boundary: Taste Lab owns profile evidence.
Setup state owns which two profiles are active.
Recommendation scoring owns ranking and explanations.
Household validation owns the product decision.

Behavior: Sophie ratings were saved and imported.
Couple-mode promotion remains deferred.

Evidence: Local SQLite counts show `80` Sophie Taste Lab rows and `34` active Sophie taste-memory events.
This evidence does not evaluate recommendation quality.

Decision: Hold the household gate until real use.
Continue offline model discovery and preflight the app's ability to capture real household evidence.
