# Taste Lab Research Brief

## Question

Can WatchSignal choose movies that teach the system more about a person's taste than arbitrary popular movies?

Short answer: yes, the hypothesis is defensible.
The exact phrase "high-signal movie" is not the standard research term, but the concept maps well to active learning, preference elicitation, value of information, item discrimination, and user cold-start recommendation.

## Working Thesis

WatchSignal should build a private Taste Lab that asks the founder to rapidly rate movies selected for preference information value.
The first goal is not to avoid rating many movies.
The first goal is to make each rating more useful than a random or popularity-only rating.

## Research Anchors

### Active learning for recommender cold start

User cold-start recommendation asks how a system can recommend well when it has little or no information about a new user.
One research direction is to choose the items that are most useful for eliciting preference information.

The item selection problem for user cold-start recommendation explicitly frames first-item selection as important for later cold-start solutions, including the first questions in an interview.
Source: [Meng et al., The item selection problem for user cold-start recommendation](https://arxiv.org/abs/2010.14013).

Cold-start recommendation by personalized embedding region elicitation argues that fixed seed sets can be suboptimal because different users need different elicitation items.
Its two-phase approach starts with a small popular-item burn-in, then asks adaptive questions chosen for value of information.
Source: [Nguyen et al., Cold-start Recommendation by Personalized Embedding Region Elicitation](https://arxiv.org/abs/2406.00973).

### Value of information

Value of information is the formal version of "ask the question whose answer most reduces uncertainty."
Collaborative filtering by personality diagnosis describes a probabilistic recommender and notes that this framework can support value-of-information computations.
Source: [Pennock et al., Collaborative Filtering by Personality Diagnosis](https://arxiv.org/abs/1301.3885).

### Item discrimination and item information

Item response theory is not movie-specific, but it provides the useful psychometric idea that some items discriminate better than others along a latent trait.
For WatchSignal, a movie can be treated as an item that reveals taste position if reactions to it separate users or taste clusters.
Source: [Item response theory overview](https://en.wikipedia.org/wiki/Item_response_theory).

### MovieLens and rating data

MovieLens is the obvious starting dataset because it provides large movie-rating datasets used in recommender research.
The current MovieLens 32M dataset contains 32 million ratings for 87,585 movies from 200,948 users.
The MovieLens Tag Genome also provides computed tag-movie relevance scores, which could help model tone and taste dimensions beyond genre.
Source: [GroupLens MovieLens datasets](https://grouplens.org/datasets/movielens/).

### Sets and belief data

MovieLens research also suggests that taste data does not have to be only individual star ratings.
Set-level ratings can convey information about multiple items at once, though individual-item ratings remain the simpler first implementation.
Source: [Sharma et al., Learning from Sets of Items in Recommender Systems](https://arxiv.org/abs/1904.12643).

The MovieLens Beliefs Dataset is relevant because it separates belief about unexperienced items from ratings after experience.
That matters for WatchSignal because "haven't seen" is not dislike, and the app should treat it differently.
Source: [Aridor et al., The MovieLens Beliefs Dataset](https://arxiv.org/abs/2405.11053).

## Definition

A high-signal movie is a movie whose rating is expected to reduce uncertainty about a user's taste more than an average candidate.

For WatchSignal, a first practical high-signal movie should have:
- enough recognizability that the user can answer quickly,
- enough ratings in a public dataset to support stable statistics,
- enough disagreement among viewers to separate taste groups,
- useful genre or tag coverage,
- low redundancy with movies already rated,
- and a clear relationship to dimensions that matter for movie-night decisions.

## Proposed First Signal Score

The first version should be simple and inspectable.
It does not need to pretend to be the final statistical model.

Candidate score:

```text
signal_score =
  recognizability
  * response_probability
  * divisiveness
  * discrimination_proxy
  * coverage_bonus
  * novelty_penalty_adjustment
```

Where:
- `recognizability` comes from rating count, popularity, release prominence, or TMDb popularity.
- `response_probability` estimates whether the founder has likely seen the movie.
- `divisiveness` can use rating variance or polarized rating share from MovieLens.
- `discrimination_proxy` estimates whether a rating on this movie predicts taste-cluster membership.
- `coverage_bonus` rewards under-covered genres, eras, tones, and Tag Genome dimensions.
- `novelty_penalty_adjustment` avoids repeatedly asking near-duplicates.

## First Data Strategy

Use MovieLens as the statistical substrate and TMDb as the display/artwork substrate.

MovieLens should provide:
- rating count,
- mean rating,
- rating variance,
- rating distribution,
- user clusters,
- item factors or embeddings,
- and tags or Tag Genome dimensions where available.

TMDb should provide:
- poster art,
- title search and ids,
- year,
- runtime,
- genres,
- popularity,
- overview,
- and public display metadata.

The first implementation can map MovieLens titles to TMDb ids by title and year, then store a curated mapping for the first queue.

## Queue Generation Plan

### Phase 1 - Burn-in

Start with 30 to 50 highly recognizable, high-coverage movies.
This phase should maximize answerability and broad taste coverage.
It should include popular movies across genre, tone, era, pacing, intensity, language, and prestige-commercial dimensions.

### Phase 2 - Adaptive refinement

After enough ratings exist, choose movies that are close to uncertain boundaries in the user's inferred taste profile.
This should prefer items whose rating would most change the user's cluster assignment, factor vector, or predicted overlap with the partner.

### Phase 3 - Couple overlap calibration

Once both people have ratings, choose items that clarify disagreement and overlap.
The system should ask about movies where one profile is uncertain, the other profile is confident, or the couple-level prediction has high variance.

## Taste Lab Product Shape

Taste Lab should be a private fast-rating tool, not part of the polished couch flow at first.

Basic loop:
1. Show 10 movies.
2. Let the user choose `Loved`, `Liked`, `Meh`, `Hated`, or `Haven't seen`.
3. Save the batch.
4. Refresh the queue.
5. Exclude already-rated movies.
6. Deprioritize `Haven't seen` movies for a while, but do not treat them as negative taste.
7. Show progress and coverage instead of pretending there is one magic required count.

## Validation Plan

The research spike should not stop at theory.
It should create a small offline experiment.

Experiment:
- Build a candidate pool from MovieLens.
- Split historical users into train and test interactions.
- Compare rating elicitation strategies at 10, 25, 50, and 100 ratings.
- Strategies to compare: popularity-only, random popular, genre-balanced, high-variance, factor-diverse, and hybrid signal score.
- Measure whether early ratings predict held-out ratings better.
- Then inspect whether the selected movie queue feels human-answerable and not weird.

Success criterion:
- The hybrid high-signal queue should outperform popularity-only on predictive utility or produce equivalent utility with better taste coverage.
- If it does not, we should still build Taste Lab, but the first queue should be honest: fast manual profile building rather than statistically optimized elicitation.

## Risks

MovieLens taste patterns may not match the founder household.
High variance can over-select weird or polarizing movies that are not useful if the founder has not seen them.
Popularity can over-select culturally obvious titles and under-map niche taste.
Tag data can encode noisy community language.
TMDb matching by title and year can create wrong joins.
The couple-overlap problem is harder than single-user preference prediction.

## Recommendation

MVP plus 1 should begin with a Taste Lab research and data spike.
The first deliverable should be an offline queue generator and a short ranked list of 100 to 200 candidate signal movies with explanation fields.
Only after that should we build the private UI for rapid rating.

## Proposed Implementation Slices

### Slice A - Offline signal-score research spike

Build a script or notebook that loads a MovieLens dataset, computes candidate signal features, and outputs a ranked high-signal movie list.
No app UI required.

### Slice B - Taste Lab storage and API

Add a private rating table for rapid taste labels.
Expose endpoints to fetch the next queue and submit a batch.

### Slice C - Private Taste Lab UI

Build a simple private route that shows 10 movie cards and lets the founder batch-rate them quickly.
It can be utilitarian at first, but it should use real poster art.

### Slice D - Recommendation evaluation

Compare recommendation behavior before and after Taste Lab ratings.
Use fixed scenarios so changes can be judged without relying only on vibes.
