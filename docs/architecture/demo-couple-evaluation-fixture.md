# Demo Couple Evaluation Fixture

The demo couple fixture gives local development a small repeatable data set for the shared household use case.
It lives in `apps/api/src/movie_night_mediator/fixtures/demo_couple.py`.

The fixture contains two generic user profiles, a shared compromise-mode session, Prime Video Germany defaults, and seven raw candidate rows.
The raw rows are converted into domain `Candidate` values by `apps/api/src/movie_night_mediator/fixtures/candidate_adapter.py`.
That adapter maps provider buckets, language fields, watched flags, and the Safe Pick classifier result into the domain shape used by scoring.

Four candidates are Safe Picks on Prime Video Germany.
Three pass through English audio metadata and one passes through verified English subtitle metadata.
One candidate is already watched and should be rejected when rewatches are off.
One candidate is only available as Amazon rent or buy and should stay out of the main shared ranking.
One candidate has Prime Video Germany flatrate availability but no verified English audio or subtitle metadata, so it should remain Needs Quick Check.

The focused smoke test lives in `apps/api/tests/test_demo_couple_fixture.py`.
It asserts the adapter-applied Safe Pick status for the fixture candidates and runs the current heuristic scorer.
The test proves that Safe Picks remain rankable, already-watched titles are filtered, and Needs Quick Check titles do not become shared recommendations by default.

This is not a broad recommender evaluation framework.
It is a stable local playground that future agents can use before touching live TMDb, UI, or LLM behavior.

The future external profile validation idea can grow from this pattern.
A later slice can add larger fixed test sets with expected likes and dislikes.
Those test sets can compare scoring changes against known outcomes without scraping, network calls, or private household data in the repo.

Later TMDb and provider adapters can replace this fixture adapter by producing the same domain fields:
provider availability buckets, original and spoken languages, explicit English audio or subtitle evidence, watched status, and a classifier-applied watchability status.
The scorer should continue to consume the domain `Candidate` shape rather than depending on a TMDb or provider-specific payload.
