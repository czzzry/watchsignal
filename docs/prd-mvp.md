# PRD - Movie Night Mediator MVP

## Problem Statement

The founder wants a private household tool that helps two people decide what to watch with less friction and better outcomes over time.
Existing movie products may already cover catalog browsing, ratings, watchlists, and general discovery.
What they do not clearly provide is a private, couch-friendly, two-person recommendation loop that learns each person's taste separately, supports household decision modes, and improves from real session outcomes.
The founder does not want a shallow filter plus popularity sort presented as a recommender.
The founder wants an MVP that may start imperfectly, but must create a measurable improvement loop and preserve a credible path toward a much more sophisticated recommendation engine.

## Solution

Build a private Movie Night Mediator with Telegram as the first interface, TMDb as the first metadata source, Google Sheets as the first operating store, and n8n as the orchestration layer.
The product should require lightweight onboarding before the first real recommendation.
It should support solo sessions, shared sessions, separate-device use, and pass-the-phone use.
For shared sessions, it should support explicit session modes such as husband-first, wife-first, and compromise.
It should return a visually rich shortlist with posters, short explanation blurbs, and visible mode-aware ranking.
It should collect pre-watch interest signals, post-watch outcome signals, watched-history corrections, and optional free-text feedback.
It should track real product metrics so that the founder can judge whether recommendation quality is improving over time.
The scoring engine should be modular and replaceable from day one so that MVP can be simple without trapping the project in a simplistic architecture.

## User Stories

1. As the founder, I want this project to remain a private household tool, so that it solves my real use case without forcing public-product complexity too early.
2. As the founder, I want the repo to preserve explicit decisions and diagrams, so that the intended architecture does not get lost during implementation.
3. As a household user, I want to interact from my phone while sitting on the couch, so that the experience feels quick and natural.
4. As a household user, I want Telegram to be the first interface, so that I can use a familiar chat surface with low setup friction.
5. As a household user, I want the system to default to movie mode unless I switch it, so that the session starts quickly in the most common case.
6. As a household user, I want the app to know who is watching first, so that recommendations can optimize for the correct audience.
7. As a solo viewer, I want the system to ignore the absent person's taste, so that the recommendation is optimized for the actual viewer.
8. As a couple, I want the app to support husband-first, wife-first, and compromise sessions, so that the recommendation objective matches the night.
9. As a couple, I want the current default mode to be shown explicitly and be easy to override, so that remembered fairness logic never becomes hidden behavior.
10. As a couple, I want the app to work when we each use our own phones, so that our inputs stay clearly separate.
11. As a couple, I want the app to also work in pass-the-phone mode, so that one device is enough when that is more convenient.
12. As a new user, I want onboarding before the first real recommendation, so that the first recommendation is not based on an empty taste model.
13. As a solo user, I want one-sided onboarding to unlock solo recommendations, so that I do not have to wait for both people before starting to use the system.
14. As a couple, I want true compromise or shared recommendations to require both users to onboard, so that the system does not pretend to understand both people when it does not.
15. As a user, I want onboarding to focus mostly on real titles I have seen, so that the initial taste model reflects actual examples rather than vague self-description.
16. As a user, I want a small preference interview for strong constraints, so that durable rules like horror tolerance are captured early.
17. As a user, I want optional prompted seeding in addition to self-supplied examples, so that the system can help when I cannot think of movies off the top of my head.
18. As a household user, I want the system to remember our common defaults between sessions, so that we do not have to repeat the same setup every time.
19. As a household user, I want Prime Germany to be easy to apply as the normal service constraint, so that the product reflects how we usually watch.
20. As a household user, I want service defaults to remain overrideable, so that we can easily switch when we are watching Netflix or another service.
21. As a household user, I want language defaults that prefer English audio or foreign-language titles with English subtitles, so that the shortlist reflects what we can actually enjoy.
22. As a household user, I want rare exceptions such as German-learning sessions to remain possible, so that the default does not become a prison.
23. As a household user, I want rewatch avoidance to be the default, so that the recommender focuses on surfacing new value rather than recycling known titles.
24. As a user, I want runtime to be available as a session constraint, so that tonight's time budget can shape the shortlist without becoming a permanent default.
25. As a user, I want a small set of hard constraints in MVP, so that obvious bad fits are screened out early.
26. As a user, I want the system to use TMDb as the first metadata source, so that the product has a rich enough catalog and artwork source for recommendations.
27. As a user in Germany, I want availability handling that takes Amazon.de into account, so that suggested titles are actually watchable for me most nights.
28. As a user, I want the system to visibly note when a data constraint may be uncertain, so that I know when the underlying data may need improvement.
29. As a user, I want a shortlist with posters or box art, so that visual recognition helps me decide quickly.
30. As a user, I want a short explanation blurb for each title, so that I can understand why it was suggested.
31. As a user, I want those blurbs to stay concise, so that the shortlist remains scannable on a phone.
32. As a user, I want the system to optimize recommendation quality over perfect interpretability, so that a stronger engine is not rejected just because it is harder to explain fully.
33. As a user, I want some human-readable rationale when possible, so that trust can grow without pretending the model is simpler than it is.
34. As a couple, I want the shortlist to show personal-fit and compromise context, so that we can understand who each title is best for.
35. As a couple on a husband-first night, I want the strongest husband-first items at the top, so that the ranking reflects the active session mode.
36. As a couple on a wife-first night, I want the strongest wife-first items at the top, so that the ranking reflects the active session mode.
37. As a couple on a compromise night, I want the strongest shared-fit candidates at the top, so that the ranking matches the compromise goal.
38. As a couple, I want compromise mode to optimize for shared enjoyment while still protecting against strong dislike, so that compromise does not collapse into bland safety.
39. As a shared-session user, I want to react to shortlist titles with Interested, Maybe, or No, so that the system can capture tonight-level intent separately from post-watch satisfaction.
40. As a shared-session user, I want to skip titles I do not have an opinion on, so that the flow stays light.
41. As a shared-session user, I want skipped items treated as unknown rather than neutral, so that the system does not over-interpret missing input.
42. As a shared-session user, I want both people to score independently before final selection, so that the system gathers cleaner data and avoids hiding disagreements.
43. As a couple, I want one person to be able to finish before the other, so that the session does not require perfectly synchronized interaction.
44. As a couple, I want unfinished sessions to pause and resume later rather than being forced into a hidden fallback, so that the tool stays respectful and low-pressure.
45. As a user, I want the reranked shortlist to remain visible after scoring, so that I can still browse the outcome rather than only being told one answer.
46. As a user, I want the app to nominate a strong single best pick, so that we can stop deliberating if we want.
47. As a user, I want a pick-for-us action, so that the app can decide decisively when we are tired of comparing options.
48. As a user, I want a refine-search path when the shortlist is weak, so that the product can rescue the session without forcing a total restart.
49. As a user, I want a start-over path too, so that I can reset the whole direction when the session assumptions were wrong.
50. As a user, I want the system to ask only the minimum questions at first, so that the flow stays fast and couch-friendly.
51. As a user, I want the system to ask more questions only when needed, so that deeper clarification happens in response to actual uncertainty.
52. As a user, I want the app to admit when it is uncertain, so that trust is not damaged by fake confidence.
53. As a user, I want a lightweight visible explanation of uncertainty, so that extra questions feel intentional and understandable.
54. As a user, I want the system to ask for more seed data when long-term taste understanding is weak, so that the corrective action matches the problem.
55. As a user, I want the system to ask more session-specific questions when tonight's context is unclear, so that the corrective action matches the problem.
56. As a user, I want to mark a title as already seen when it appears in a shortlist, so that the mistake becomes useful history rather than wasted effort.
57. As a user, I want already-seen correction to optionally capture Loved, Fine, or No, so that watched-history backfill also improves taste modeling.
58. As a user, I want a lightweight manual watched-history backfill flow outside live sessions, so that the system can learn from past viewing without waiting for future nights.
59. As a couple, I want a quick we-both-watched-this path, so that history backfill stays fast without merging our taste profiles together.
60. As a user, I want post-watch feedback to be captured separately for each person, so that the system learns both taste models correctly.
61. As a user, I want post-watch feedback to use Loved, Fine, or No, so that the model gets useful signal without requiring an exhausting rating scale.
62. As a user, I want optional free-text reasons when we pick something else or reject the shortlist, so that future versions can learn from richer context.
63. As a user, I want free-text feedback stored safely from day one even if MVP does not interpret it deeply yet, so that MVP plus 1 has better historical material to work with.
64. As a user, I want the next session to ask what we actually watched, so that the feedback loop survives even when we do not rate immediately after the movie.
65. As a user, I want to say we watched the recommended movie, watched something else, or watched nothing, so that the system can distinguish different failure and success modes.
66. As the founder, I want the product to track whether shortlist usage, restarts, and feedback trends improve over time, so that recommendation quality can be judged by real outcomes rather than intuition.
67. As the founder, I want a lightweight visible history of sessions and outcomes, so that I can tell whether the system is actually learning.
68. As the founder, I want deeper session artifacts stored internally, so that debugging, evaluation, and future diagrams can be grounded in real runs.
69. As the founder, I want an on-demand profile snapshot later, so that I can inspect what the system thinks about each person's taste without cluttering the daily flow.
70. As the founder, I want the MVP architecture to preserve an explicit MVP plus 1 lane, so that the path to stronger recommendation sophistication is not forgotten once the first slice works.
71. As the founder, I want diagrams maintained as part of the project, so that architecture remains understandable while the system evolves.
72. As the founder, I want the scoring engine behind a clean replaceable boundary, so that the recommendation core can become more sophisticated later without rewriting the whole product.
73. As the founder, I want MVP plus 1 to focus on LLM-assisted interpretation of human feedback, so that the system becomes meaningfully smarter in how it learns from real sessions.
74. As the founder, I want the repo to remain the private source of truth first, so that development can stay honest and secure before any public artifact exists.

## Implementation Decisions

- The first release target is one complete vertical slice, not broad platform coverage.
- Telegram is the first interface and must support both separate-device and pass-the-phone interaction styles.
- The product is movie-first by default, but TV support is in scope for MVP at the intake and recommendation level.
- Episode-level recommendation inside already-known TV series is out of MVP and belongs to a later phase.
- TMDb is the primary metadata source for MVP.
- Availability and language constraints must explicitly account for the founder's Germany-based viewing context.
- Amazon.de availability is a practical requirement for common sessions.
- English audio, or foreign-language titles with English subtitles, is the default language posture for normal use.
- Google Sheets is the first operating store because it supports n8n learning, inspectability, and fast iteration.
- n8n is responsible for orchestration, state transitions, messaging, and integration wiring.
- Scoring and recommendation logic should live behind a separate, testable scoring boundary rather than being buried inside n8n nodes.
- The first scoring engine should be simple but credible, with explicit allowance for later sophistication upgrades.
- Recommendation quality matters more than full transparency, but explanations remain a user-facing trust feature.
- Session mode is a first-class input and shapes ranking behavior.
- Shared sessions must support husband-first, wife-first, and compromise modes.
- Compromise mode should optimize first for strong shared enjoyment with dislike protection as a guardrail.
- The product should remember common defaults between sessions and make those defaults visible and easy to override.
- Runtime is session-level rather than a remembered household default.
- Rewatch avoidance is a remembered household default.
- Onboarding is required before first real recommendations, with one-sided onboarding allowed for solo use.
- Shared recommendation mode requires both users to have onboarded.
- Onboarding should lean heavily on title-based seeding and only lightly on preference-interview questions.
- Prompted rating should exist to help users who struggle to recall good seed examples unaided.
- Shortlist reactions and post-watch reactions are separate signals and should use different scales.
- Skips in shortlist reactions should be treated as unknown rather than neutral.
- Optional free-text feedback should be captured from day one, even if MVP only stores it and later versions interpret it more deeply.
- Watched-history correction and manual backfill are in MVP because recommendation trust depends on good watched-state quality.
- The first planned sophistication upgrade after MVP is LLM-assisted interpretation of free-text feedback and rejection reasons.
- Version one should use n8n Cloud if convenient, but portability to self-hosted n8n is a design constraint from the start.
- The repo is the private source of truth first, and any public portfolio artifact should be derived and sanitized later.

## Testing Decisions

- Good tests should verify external behavior through public seams, not implementation details.
- The highest-priority seams are the scoring-module contract, the session-state transition behavior, the shortlist reaction flow, the outcome-capture flow, and the persistence of session artifacts and feedback.
- Recommendation tests should focus on observable ranking behavior under different session modes and constraints rather than testing internal formula steps directly.
- Workflow tests should focus on end-to-end user-visible transitions such as onboarding completion, shortlist generation, shared-session progression, timeout pause behavior, and post-watch reconciliation.
- Data-store tests should verify that the visible operating store reflects the correct session outcomes, watched history, and metrics without requiring the user to understand internal internals.
- MVP should favor integration-style tests at the seam between orchestration and scoring, because that is where long-term architecture risk is highest.
- Portability-sensitive behavior should be tested through contracts and behavior rather than through assumptions tied to n8n Cloud specifics.
- Metrics tracking should be verified as product behavior, because trend visibility is part of the value proposition rather than a purely internal concern.

## Out of Scope

- Public product release
- Open-source starter or public template packaging
- Accepted ADR creation beyond what is already explicitly approved later
- Production deployment to multiple environments
- Final long-term recommendation sophistication
- LLM-driven ranking authority
- Episode-level recommendation within already-known TV series
- Deep profile visualization in MVP
- Ideal-movie synthesis in MVP
- Rich analytics dashboards in MVP
- Multi-user household support beyond the two-person use case
- Additional metadata or availability vendors unless a concrete gap appears
- Browser or TV-native front ends

## Further Notes

- Alignment work is already embodied in the current planning set rather than a separate named alignment skill.
- The alignment package for this project is primarily:
  - `docs/founder-decisions.md`
  - `docs/decision-register.md`
  - `docs/decision-grill.md`
  - `docs/research/research-evidence-map.md`
  - `docs/workflow-map.md`
  - `docs/architecture-overview.md`
- The recommended next skills flow is `to-issues` followed by `tdd`.
- GitHub publishing is not yet possible because this repo does not currently have a remote configured.
- Until a remote exists, this PRD should be treated as the canonical local draft.
