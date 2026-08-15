# S23 live-result trust and visual risk closure builder handoff

## Claim

Normal live TMDB results can use the approved cinematic backdrop treatment, and the default result sentence is specific to the movie and the household evidence that actually exists.

## Contract

The verified TMDB `backdrop_path` travels through `Candidate.backdrop_url`, `OfflineShortlistItem.backdrop_url`, `RecommendationShortlistItemPayload.backdropUrl`, the generated web contract, and the existing result view model.
The public reason uses the title, the exact recorded reactions, and only recognized structured evidence such as a confirmed person request, a tonight-intent match, positive saved genre evidence, saved movie history, or measured profile overlap.
When none of those preference signals exists, the sentence uses only verified movie genres and does not imply a preference match.

## Boundary

TMDB metadata ownership remains in the candidate source adapter.
The shortlist and API layers only transport the verified URL and structured evidence.
The web helper owns the concise public sentence.
The result component, Match Index, provider behavior, shortlist ordering, recommendation weights, and demo fixture are unchanged.

## Behavior

The live result stage receives a landscape TMDB URL and continues to use its existing missing-image fallback if the URL is absent or the image fails.
The generic `model fit`, mood, tone, and runtime result sentence is replaced by deterministic copy grounded in the selected title and current household evidence.
No LLM claim or hidden scoring detail is presented to the household.

## Evidence

- The red API contract failed first because `Candidate` had no `backdrop_url`.
- The red web contract failed first because structured evidence was dropped and `describeSharedWhy` returned the generic mood/model sentence.
- Focused TMDB and shortlist API tests passed: 37 of 37.
- Full API tests passed: 353 of 353.
- Focused result, Match Index, accessibility, and session lifecycle tests passed: 41 of 41.
- New live-result trust tests passed: 4 of 4.
- Full web state tests passed: 213 of 213.
- TypeScript passed with no output.
- The production Next.js build passed and generated all 33 static pages.
- Scoped diff checking passed.
- Browser capture is unproven because the browser runtime reported zero available browsers even though `http://localhost:3110/` returned HTTP 200.

## Decision

Hand off for an independent critic.
No acceptance claim is made by the builder.
