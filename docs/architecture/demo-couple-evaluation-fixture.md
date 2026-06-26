# Demo Couple Evaluation Fixture

The demo couple fixture gives local development a small repeatable data set for the shared household use case.
It lives in `apps/api/src/movie_night_mediator/fixtures/demo_couple.py`.

The fixture contains two generic user profiles, a shared compromise-mode session, Prime Video Germany defaults, and four candidates.
Two candidates are Safe Picks on Prime Video Germany with English language metadata.
One candidate is already watched and should be rejected when rewatches are off.
One candidate is only available as Amazon rent or buy and should stay out of the main shared ranking.

The focused smoke test lives in `apps/api/tests/test_demo_couple_fixture.py`.
It first runs the Safe Pick classifier over the fixture candidates.
It then applies those classifications to the candidates and runs the current heuristic scorer.
The test proves that Safe Picks remain rankable, already-watched titles are filtered, and Needs Quick Check titles do not become shared recommendations by default.

This is not a broad recommender evaluation framework.
It is a stable local playground that future agents can use before touching live TMDb, UI, or LLM behavior.

The future external profile validation idea can grow from this pattern.
A later slice can add larger fixed test sets with expected likes and dislikes.
Those test sets can compare scoring changes against known outcomes without scraping, network calls, or private household data in the repo.
