# PRD - Scoring V2 Recommendation Engine

## Problem Statement

The current recommendation engine is good enough to prove the code-first product loop, but it is not yet the mature engine the founder has in mind.
It relies on a simple, inspectable heuristic scorer that is strong enough for watchability, basic Taste Lab carryover, session-mode weighting, and lightweight tonight-intent movement.
That is the right shape for version one, but it is now visibly hitting its ceiling in real dogfooding.
Natural-language nudges can be misread or only partially honored.
Negative preference handling is too shallow for requests like “no kids movies,” “no cartoonish stuff,” or richer “not this, more that” phrasing.
Candidate ranking still leans too heavily on coarse genre evidence and a narrow set of feature-tag affinities.
The founder wants a recommendation engine that uses much more of the available metadata and household history, while still staying explainable, testable, and replaceable.

## Solution

Build a V2 scoring engine as a separate recommendation phase after the current MVP+7 stabilization work.
Keep the current watchability rules, active session modes, Prime Germany policy, and couch-flow product shape intact.
Upgrade the ranking engine from a small heuristic scorer into a richer hybrid scorer that combines structured metadata, person-specific memory, pairwise household fit, stronger negative-preference handling, and better compiled tonight-intent signals.
Keep candidate generation, watchability filtering, intent interpretation, and final ranking as distinct responsibilities so the system stays debuggable.
Expose better evidence so the UI can explain why something won without pretending the engine is simpler than it is.
Preserve a safe fallback path when the richer model is uncertain or over-constrained instead of forcing a misleading top pick.

## User Stories

1. As a founder, I want the next scorer to use much more of the movie metadata, so that recommendations feel materially smarter than a genre-weighted heuristic.
2. As a founder, I want cast, crew, keywords, themes, tone, and language signals to matter when they are relevant, so that recommendations can reflect subtler taste.
3. As a founder, I want negative preferences to be handled explicitly, so that “avoid this kind of thing” works as reliably as “more like this.”
4. As a founder, I want the engine to distinguish hard constraints from soft ranking signals, so that watchability and recommendation quality do not get blurred together.
5. As a solo user, I want the app to understand that I may love some dramas and hate others, so that genre alone does not dominate the ranking.
6. As a solo user, I want the app to learn from my Taste Lab ratings, shortlist reactions, watched history, and post-watch feedback together, so that the engine reflects my actual taste over time.
7. As a solo user, I want named-person nudges to influence both candidate generation and ranking, so that “Josh Brolin” feels different from a generic action request.
8. As a solo user, I want natural-language nudges to be compiled into structured signals that can express inclusion, exclusion, intensity, and uncertainty, so that the app handles richer directions honestly.
9. As a solo user, I want the app to tell me clearly when only part of my nudge can be honored, so that I know what the engine is really using.
10. As a solo user, I want a high-quality “no match” state when my nudges are too restrictive, so that failure feels honest instead of broken.
11. As a couple, we want compromise mode to reflect both overlap and veto risk, so that one person does not get steamrolled by the other’s stronger signal volume.
12. As a couple, we want the app to notice bridges between our tastes, so that compromise can find genuinely shared wins instead of safe-but-dull middle ground.
13. As a couple, we want the scorer to remember which kinds of picks repeatedly fail for one of us, so that the same mismatch does not keep resurfacing.
14. As a couple, we want the engine to separate household overlap from individual fit, so that the explanation can say whether something is a personal win, a compromise win, or a bridge win.
15. As a product lead, I want the scorer to remain testable through fixed evaluation cases, so that sophistication does not come at the cost of trust.
16. As a product lead, I want the engine to be measurable with before-and-after evaluation outputs, so that upgrades are judged by ranking quality rather than intuition alone.
17. As a product lead, I want the app to preserve a stable debug surface for recommendation evidence, so that we can inspect why a surprising title rose or fell.
18. As a product lead, I want the engine to degrade gracefully when metadata is sparse, so that partial enrichment does not produce nonsense rankings.
19. As a product lead, I want live TMDb recommendations to stay fast enough for couch use, so that a richer scorer does not make the app feel sluggish.
20. As a product lead, I want the V2 scorer to keep the existing replaceable scoring boundary, so that future versions can still swap out ranking logic without rewriting the product.
21. As a coding agent, I want candidate generation and scoring to remain separate, so that person filters, keyword fetches, and final ranking can evolve independently.
22. As a coding agent, I want tonight-intent interpretation to compile into a richer structured nudge contract, so that ranking logic does not need to guess from raw sentences alone.
23. As a coding agent, I want negative preference concepts like kids, Pixar-like, cartoonish, saccharine, bleak, or slow to map into canonical scoring concepts, so that the engine handles equivalent phrasing consistently.
24. As a coding agent, I want the engine to use reusable canonical vocabularies for metadata facets, so that tests and explanations stay stable while internals improve.
25. As a coding agent, I want the engine to support weighted evidence families, so that metadata contributions can be tuned without rewriting the whole scorer.
26. As a coding agent, I want user memory sources to be weighted by recency, source reliability, and explicitness, so that a single old seed does not overpower repeated recent behavior.
27. As a coding agent, I want shortlist reactions to behave differently from post-watch outcomes, so that a lightweight maybe/no gesture is not treated the same as a real watched result.
28. As a coding agent, I want the engine to recognize repeated title, keyword, and concept patterns across liked and disliked items, so that the system can learn beyond literal genre buckets.
29. As a coding agent, I want a clear fallback ladder when the full metadata scorer has low confidence, so that the system can step down safely rather than return opaque failures.
30. As a future maintainer, I want the V2 engine to remain partially explainable in product language, so that we can show users useful reasons without exposing unreadable internals.

## Implementation Decisions

- This PRD is a next-phase backlog candidate and not part of the accepted MVP+7 refactor scope.
- The current MVP+7 phase remains a stabilization phase.
- V2 scoring should begin only after the current bug-fix and stabilization work is landed cleanly.
- Watchability remains upstream of ranking.
- Provider access, language access, watched-state rules, and household constraints should still determine whether a title is eligible before the scorer decides its order.
- Candidate generation and candidate scoring remain separate modules.
- Person filters, keyword expansions, and other retrieval strategies may broaden or narrow the candidate set, but they should not directly choose the winner.
- Tonight-intent should compile into a richer structured nudge contract before ranking.
- The V2 scorer should consume structured positive signals, negative signals, emphasis strength, confidence, and any partially unsupported notes rather than reinterpreting raw prose where avoidable.
- The scoring engine should move from a single flat heuristic into a layered model.
- The layers should include at least:
  - eligibility and hard-constraint checks,
  - candidate retrieval and enrichment,
  - per-user affinity scoring,
  - shared-session reconciliation,
  - shortlist shaping and abstain-or-fallback behavior.
- Per-user affinity scoring should use more metadata than the current genre and feature-tag mix.
- Candidate facets should include, when available and reliable:
  - genres,
  - keywords,
  - overview themes,
  - cast,
  - crew,
  - franchise and series adjacency,
  - runtime and pacing proxies,
  - tone and mood concepts,
  - language and region signals,
  - safety and accessibility fields already present in the product.
- The system should introduce canonical scoring concepts that sit above raw TMDb fields.
- Examples include concepts like animation, family, bleak, cozy, cerebral, romantic, procedural, manhunt, ensemble, courtroom, first-contact, or revenge.
- Raw provider metadata should not become the long-term scoring vocabulary.
- The engine should learn from multiple evidence sources with source-specific weighting.
- Evidence sources should include:
  - onboarding seeds,
  - Taste Lab ratings,
  - shortlist Interested or Maybe or No reactions,
  - watched-history backfill,
  - post-watch Loved or Fine or No outcomes,
  - optional saved-note or free-text interpretation outputs once those are mature enough.
- Evidence should be weighted by both source type and freshness.
- Post-watch outcomes should generally outweigh lightweight shortlist reactions.
- Repeated consistent signals should outweigh one-off weak signals.
- Negative evidence should be first-class.
- The engine should store and score dislike concepts explicitly instead of modeling everything as missing positive fit.
- Household scoring should become richer than the current least-misery plus average blend.
- Shared ranking should consider:
  - each user’s independent fit,
  - veto risk,
  - overlap strength,
  - bridge-value between adjacent tastes,
  - repeated mismatch avoidance from prior nights.
- The system should support a confidence or certainty output for the winning pick.
- If top candidates are weak or the nudge stack is too restrictive, the engine should be able to say so explicitly instead of forcing a confident-sounding best pick.
- The engine should preserve inspectable evidence families for product trust and debugging.
- V2 explanations do not need to expose every internal weight, but they should expose the dominant winning reasons and dominant penalties.
- Ranking evidence should remain tied to stable concept labels rather than internal method names where possible.
- The engine should define a deliberate fallback ladder.
- If the richest scorer cannot run because metadata is sparse, time budget is exceeded, or confidence is low, the system should fall back to a simpler but safe ranking path rather than failing silently.
- The current Prime Germany policy remains unchanged.
- Prime flatrate, rent, and buy continue to count as valid access in Germany as long as the other active constraints still pass.
- V2 scoring should not change the accepted product rule that the shortlist still contains five titles when enough eligible candidates exist.
- The shortlist should still reserve room for an interesting but safe option when the engine has evidence for one.
- The engine should support both solo and shared recommendation flows without forking into unrelated products.
- The debug-history and evaluation surfaces should evolve with the scorer rather than being abandoned.
- V2 should introduce an explicit concept registry or equivalent canonical facet layer so free-text nudges, metadata enrichment, and evidence explanation all speak the same language.
- V2 should keep LLM use bounded and honest.
- LLMs may help interpret free text, cluster notes, or enrich concept maps, but the final ranking contract should remain structured and testable rather than becoming an opaque chat output.

## Testing Decisions

- Good tests for the V2 scorer verify external behavior, stable ordering changes, visible evidence, confidence surfaces, and explicit fail states rather than internal helper structure.
- Existing evaluation seams should be extended rather than replaced where possible.
- The highest-value tests are likely:
  - fixed-scenario ranking comparisons,
  - before-and-after evaluation harness runs,
  - directed-nudge interpretation and scoring integration tests,
  - solo and shared shortlist API tests,
  - no-results and low-confidence behavior tests,
  - debug-history evidence surface tests.
- A good scoring test should say what the engine should prefer or avoid, not which internal contribution function fired.
- Tests should prefer observable ranking shifts and explanation families over brittle exact-weight assertions.
- Weight-level assertions should be rare and limited to places where a specific invariant is critical.
- The scorer should gain a dedicated evaluation corpus with named scenarios covering:
  - strong negative kid-animation requests,
  - actor-driven retrieval and ranking,
  - subtle tone matches,
  - household bridge picks,
  - repeated mismatch suppression,
  - high-confidence solo favorites,
  - legitimate “no strong match” outputs.
- The evaluation harness should compare the current scorer and the proposed scorer on the same corpus and produce a readable delta report.
- The API contract should be tested so richer scoring evidence and confidence fields do not drift silently.
- Prior art already exists in the repo for:
  - heuristic scorer behavior tests,
  - shortlist API tests,
  - tonight-intent tests,
  - evaluation report generation,
  - debug-history evidence payloads.
- V2 should reuse those seams and deepen them instead of inventing a parallel untested path.
- Performance tests should be included for live recommendation latency.
- A richer scorer that becomes too slow for couch use should be treated as a failed implementation even if its ranking quality improves offline.
- Dogfood validation should remain part of the acceptance story.
- The founder should be able to inspect a few concrete recommendation sessions and understand why the new scorer is better, not just that an offline metric moved.

## Out of Scope

- Rewriting the entire app.
- Replacing TMDb as the first metadata source.
- Changing the current Amazon DE access policy.
- Turning the recommender into a fully opaque LLM-only ranker.
- Public multi-user account infrastructure.
- A complete redesign of the pass-the-phone UI as part of the scorer upgrade alone.
- Solving every future recommender problem in one phase.
- Building a production-scale machine-learning platform before the scoring concepts are proven locally.

## Further Notes

- The immediate bug batch fixed in the current work should be treated as correctness repair for V1, not as the V2 scorer itself.
- The product should not confuse “stronger engine” with “more mysterious engine.”
- The V2 scorer should feel smarter, but also more honest about uncertainty, partial understanding, and over-constrained sessions.
- The likely execution order after MVP+7 is:
  - finalize scorer concepts and evaluation corpus,
  - upgrade the nudge contract,
  - add richer metadata and memory features,
  - improve household reconciliation,
  - validate speed and trust surfaces,
  - only then replace the current default scorer.
- Publishing this PRD to GitHub Issues should wait for explicit founder approval because that is still an external service change for this repo.
