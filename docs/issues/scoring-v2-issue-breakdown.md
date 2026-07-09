# Scoring V2 Issue Breakdown

This proposed issue set breaks [docs/prd-scoring-v2.md](../prd-scoring-v2.md) into bounded vertical slices.
It is a local draft for Phase 3 planning and has not been published to GitHub Issues.

## Current MVP Phase

Phase 3 is **Scoring V2 Recommendation Engine**.
The Phase 3 slice plan is accepted for local execution.

Current tracker:

```text
Scoring V2: [####################] 14/14 issues done
```

MVP+7 is already complete.
This phase starts after the landed MVP+7 stabilization and follow-up fixes.
New work discovered during execution should be classified as in-scope risk closure, a scope-change candidate that needs founder approval, or next-phase backlog.
The issue count is fourteen: one planning spike, twelve implementation slices, and one promotion decision slice.

## Phase Promise

WatchSignal can compare the current V1 heuristic scorer against a richer V2 scorer on fixed recommendation scenarios, then safely promote V2 once it proves better ranking, clearer evidence, honest uncertainty, and acceptable couch-flow latency.

The phase is done only when all of these are true:

- A fixed evaluation corpus shows before-and-after scorer behavior for solo, shared, directed-nudge, negative-preference, and no-strong-match scenarios.
- The richer scorer consumes canonical scoring concepts instead of raw provider metadata as its long-term vocabulary.
- Current watchability, Prime Germany, shortlist-size, and session-mode rules remain unchanged unless the founder explicitly approves a product decision change.
- The pass-the-phone recommendation flow still returns a usable shortlist quickly enough for couch use.
- Debug and product explanation surfaces expose dominant positive evidence, dominant penalties, confidence, and partial-support notes without turning ranking into an opaque LLM output.

## Product Invariants

- Watchability remains upstream of ranking.
- Prime Germany access policy remains unchanged.
- Prime flatrate, rent, and buy remain valid German access paths when other active constraints pass.
- Shared-session modes remain `husband_first`, `wife_first`, and `compromise`.
- Session-mode ranking semantics may become richer, but the mode contract must not disappear or fork into unrelated products.
- Candidate generation and candidate scoring remain separate responsibilities.
- V2 is a whole-recommender upgrade, not a nudge-parser upgrade.
- V2 must enrich both user profiles and candidate movies before scoring, using durable taste memory, candidate metadata, session context, and confidence signals.
- The shortlist still contains five titles when enough eligible candidates exist.
- Existing debug-history and evaluation seams should be extended rather than replaced.
- LLM use, if any, remains bounded to interpretation or enrichment support and must compile into structured, testable contracts.

## Proposed GitHub Tracker

Parent PRD issue:

- Not yet created.
- Publishing issues is an external service change and needs explicit founder approval.

Implementation and acceptance slices:

- Planning Spike - Scoring Data Richness Inventory
- Slice 1 - Evaluation Corpus And V1 Baseline
- Slice 2 - V2 Contract And Scorer Selection Flag
- Slice 3 - Canonical Concept Registry Tracer Bullet
- Slice 4 - Profile And Candidate Concept Evidence Feed Ranking
- Slice 5 - Structured Nudge Signals Feed Ranking
- Slice 6 - Negative Preference Penalties And Honest Partial Support
- Slice 7 - Metadata Evidence Families For Solo Fit
- Slice 8 - Multi-Source Memory Weighting
- Slice 9 - Shared Household Reconciliation Upgrade
- Slice 10 - Confidence, Abstain, And Fallback Ladder
- Slice 11 - Debug Evidence And UI Explanation Surface
- Slice 12 - Live Latency And Phone-Sized Dogfood Gate
- Slice 13 - V2 Default Promotion Decision

## Planning Spike - Scoring Data Richness Inventory

- Type: AFK with HITL review before adopting any new paid provider or external dependency
- Suggested labels: `ready-for-agent`
- Blocked by: None
- User stories covered: 1, 2, 18, 19, 20, 24, 25
- Primary goal: identify the richest practical data sources and fields V2 can use before designing the evaluation corpus around them.
- User-facing change: As a founder, I will be able to see what recommendation evidence is realistically available, useful, explainable, and fast enough before we build V2 around it.
- Status: Done locally in [docs/scoring-v2-data-research-spike.md](../scoring-v2-data-research-spike.md).

### What to build

Audit the data already available in the app, the fields available from the current TMDb integration, local enrichment fixtures, Taste Lab outputs, watched history, shortlist reactions, post-watch feedback, and debug snapshots.
Classify each possible signal by recommendation value, availability, latency risk, cacheability, explainability, privacy sensitivity, testability, and whether it belongs in candidate generation, enrichment, scoring, or explanation.
Produce a short recommendation for the first V2 evidence families to use and the fields to defer.

### Acceptance criteria

- [x] The inventory lists current local fields used by V1 and currently unused fields already available in app payloads.
- [x] The inventory lists promising TMDb fields or appendable metadata that could improve V2 without replacing TMDb.
- [x] Each candidate signal is classified as candidate-generation, enrichment, scoring, explanation, or debug-only.
- [x] Each candidate signal is rated for recommendation value, latency risk, cacheability, explainability, and testability.
- [x] The spike identifies which evidence families should be included in the first evaluation corpus.
- [x] The spike explicitly calls out any data source that would require founder approval because it adds network usage, paid vendors, secrets, or privacy sensitivity.
- [x] The spike ends with a recommended V2 data starting set and a deferred list.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when Slice 1 can build an evaluation corpus around the best practical data, not just the data V1 already uses.

### Risk notes

This spike should not add new providers, fetch large datasets, or change runtime scoring behavior.
It is a bounded research and architecture note.

## Slice 1 - Evaluation Corpus And V1 Baseline

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Planning Spike - Scoring Data Richness Inventory
- User stories covered: 15, 16, 17, 18, 19
- Primary goal: create the measurement harness before ranking semantics change.
- User-facing change: As a founder, I will be able to see where the current scorer succeeds and fails before we change its behavior.
- Status: Done locally through `pnpm eval:scoring-v2:v1`, [docs/validation/scoring-v2-v1-baseline.md](../validation/scoring-v2-v1-baseline.md), and [docs/validation/scoring-v2-v1-baseline.json](../validation/scoring-v2-v1-baseline.json).

### What to build

Add a fixed scorer-evaluation corpus with named scenarios for negative kid-animation requests, actor-driven requests, subtle tone matches, household bridge picks, repeated mismatch suppression, high-confidence solo favorites, and legitimate no-strong-match outcomes.
Run the current V1 heuristic scorer against the corpus and produce a readable baseline report that records ordering, evidence, uncertainty, and known misses.

### Acceptance criteria

- [x] The corpus includes named solo, shared, directed-nudge, negative-preference, and no-strong-match scenarios.
- [x] Each scenario declares expected preference or avoidance behavior without depending on exact internal weights.
- [x] Each scenario declares expected dominant concepts, penalties, confidence, and explanation behavior where relevant.
- [x] The current V1 scorer can run across the corpus without changing product behavior.
- [x] The baseline report identifies where V1 succeeds, where it partially supports a scenario, and where it misses.
- [x] The report is committed as a reviewable artifact or generated from committed fixtures.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when future scorer work can prove improvement against a stable baseline instead of relying on intuition.

### Risk notes

Keep the first corpus small enough to maintain.
This slice measures the current engine and does not replace it.

## Slice 2 - V2 Contract And Scorer Selection Flag

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 1
- User stories covered: 4, 17, 18, 20, 21, 29, 30
- Primary goal: introduce the V2 scoring contract with a reversible scorer-selection seam.
- User-facing change: As a founder, I will be able to try a richer scorer safely without losing the current working recommendation path.
- Status: Done locally through the V2 contract scorer selection seam and focused contract tests.

### What to build

Extend the scoring contract so a V2 scorer can return structured evidence families, confidence, dominant penalties, partial-support notes, and fallback reasons.
Add a local scorer-selection mechanism that can run V2 and preserve V1 as a rollback scorer.

### Acceptance criteria

- [x] V2 is now the default scorer after the Slice 13 founder promotion decision.
- [x] V1 can be selected explicitly in tests or local rollback runs.
- [x] The output contract can represent dominant positive evidence, dominant penalties, confidence, partial support, and fallback reason.
- [x] Existing shortlist API behavior remains compatible for current UI consumers.
- [x] Contract tests prevent silent drift in the richer evidence payload.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when V2 can be exercised safely behind a controlled boundary while V1 remains available.

### Risk notes

Do not use this slice to tune ranking.
It is the seam that lets later slices stay reversible.

## Slice 3 - Canonical Concept Registry Tracer Bullet

- Type: AFK with HITL review if concept names imply product meaning changes
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 2
- User stories covered: 2, 23, 24, 25, 30
- Primary goal: prove one canonical scoring vocabulary path from metadata and nudges into evidence.
- User-facing change: As a user, I will get recommendations that understand stable taste concepts like cozy, bleak, cerebral, animation, or revenge rather than only raw genres.
- Status: Done locally through the V2 concept registry tracer bullet and focused concept tests.

### What to build

Introduce a small concept registry or equivalent canonical facet layer for a first set of concepts such as animation, family, bleak, cozy, cerebral, romantic, procedural, revenge, and first-contact.
Map a narrow set of genres, keywords, overview terms, and known nudge phrases into those concepts.
Expose the resulting concept evidence in V2 evaluation output.

### Acceptance criteria

- [x] Raw TMDb genres, keywords, and overview terms can map into stable concept labels.
- [x] A small negative-preference vocabulary maps equivalent phrasing into the same concepts.
- [x] Unmapped metadata remains valid and does not make candidates unrankable.
- [x] V2 evidence shows concept labels rather than raw parser internals.
- [x] Evaluation scenarios can assert observable concept-driven ranking shifts.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when one thin metadata-to-concept-to-score path works end to end.

### Risk notes

This is not the final ontology.
Keep concept names plain enough for product explanations.

## Slice 4 - Profile And Candidate Concept Evidence Feed Ranking

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 3
- User stories covered: 1, 2, 5, 6, 24, 25, 26, 28
- Primary goal: make enriched profile evidence and enriched candidate concepts feed the V2 scorer before nudge behavior becomes the main focus.
- User-facing change: As a user, I will get recommendations shaped by my profile's learned taste concepts and each movie's richer concept evidence, not just genre overlap or tonight's nudge.
- Status: Done locally through profile concept affinities, candidate concept matching, and V2-only reranking tests.

### What to build

Connect the concept registry to both sides of the match.
Profile evidence from onboarding seeds, Taste Lab ratings, watched history, and post-watch feedback should compile into stable liked and disliked concepts.
Candidate metadata should compile into the same concept vocabulary.
The V2 scorer should expose profile-concept fit and candidate-concept evidence without replacing V1 as the default app scorer.

### Acceptance criteria

- [x] Profile evidence can compile into positive and negative concept affinities.
- [x] Candidate metadata can compile into the same concept labels.
- [x] V2 can expose concept overlap between a profile and a candidate.
- [x] V2 can expose concept mismatch between a profile and a candidate.
- [x] Ranking tests show concept evidence can move V2 ordering in local evaluation while V1 remains available.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when V2 can demonstrate profile-to-candidate concept matching as a whole-recommender improvement independent of directed nudges.

### Risk notes

Do not collapse this into raw genre scoring.
The point is to prove reusable taste concepts from profile memory and candidate metadata.

## Slice 5 - Structured Nudge Signals Feed Ranking

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 4
- User stories covered: 7, 8, 9, 21, 22, 23
- Primary goal: make compiled tonight intent affect V2 ranking without reinterpreting raw prose inside the scorer.
- User-facing change: As a user, I will be able to steer tonight's recommendations with natural language and see the app use the parts it understood.
- Status: Done locally through structured tonight-intent session contracts, V2 nudge evidence, and directed-nudge API regression tests.

### What to build

Extend the tonight-intent contract so positive signals, negative signals, intensity, confidence, unsupported clauses, and person requests are available to V2 scoring.
Use those structured signals in V2 ranking and evidence while preserving candidate-generation responsibilities for person and keyword retrieval.

### Acceptance criteria

- [x] The nudge contract distinguishes inclusion, exclusion, intensity, confidence, and unsupported notes.
- [x] The V2 scorer consumes the structured contract rather than parsing raw free text.
- [x] Person nudges remain represented for candidate retrieval and ranking evidence without directly choosing the winner.
- [x] Existing directed-nudge API tests continue to pass.
- [x] Evaluation scenarios show nudge-driven ranking movement and partial-support honesty.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when a directed nudge can move V2 rankings and explain what was understood.

### Risk notes

Preserve current parser repairs for person names and exclusion signals.
Do not regress the existing "could not find five movies" shortage messaging.

## Slice 6 - Negative Preference Penalties And Honest Partial Support

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 5
- User stories covered: 3, 8, 9, 10, 23, 29
- Primary goal: make avoid requests first-class ranking signals with visible consequences.
- User-facing change: As a user, I will be able to say what I do not want tonight and have those dislikes visibly lower the wrong kinds of movies.
- Status: Done locally through structured negative nudge penalties, partial-support notes, and focused V2 ranking tests.

### What to build

Add V2 penalties for canonical negative concepts such as kids, family-animation, cartoonish, saccharine, bleak, and slow where evidence supports them.
Return explicit partial-support and over-constrained-session notes when only part of an avoid request can be honored.

### Acceptance criteria

- [x] "No kids movies" penalizes family-animation evidence without becoming a broad ban on every light movie.
- [x] "No cartoonish stuff" penalizes animation or cartoonish concepts when metadata supports them.
- [x] Positive and negative signals can coexist in the same nudge without one silently erasing the other.
- [x] The result can say which part of a request was unsupported or only partially supported.
- [x] Evaluation scenarios prove relevant candidates fall below better-matching alternatives.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when negative preferences are represented as explicit evidence and penalties, not missing positives.

### Risk notes

Keep hard constraints separate from soft penalties.
Do not move watchability decisions into the scorer.

## Slice 7 - Metadata Evidence Families For Solo Fit

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 6
- User stories covered: 1, 2, 5, 18, 25, 28
- Primary goal: make solo V2 scoring materially richer than genre overlap.
- User-facing change: As a solo user, I will get picks that reflect subtler metadata such as themes, cast, crew, tone, pacing, and language instead of mostly genre.
- Status: Done locally through tunable V2 metadata family weights, solo ranking tests, and fallback evidence tests.

### What to build

Extend V2 solo affinity scoring to use weighted evidence families for genres, canonical concepts, keywords, overview themes, cast, crew, franchise or series adjacency, runtime and pacing proxies, tone and mood concepts, language, and region where data is available.
Sparse metadata should degrade safely to the existing simpler evidence path.

### Acceptance criteria

- [x] Candidate evidence can include multiple weighted metadata families.
- [x] Sparse candidates remain rankable with clear fallback evidence.
- [x] Feature families can be tuned without rewriting the scorer.
- [x] Ranking tests verify richer evidence changes ordering in named scenarios.
- [x] Explanations identify dominant metadata families in product language.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when V2 solo ranking can beat the V1 baseline on at least one subtle metadata scenario without losing safe fallback behavior.

### Risk notes

Avoid pretending every provider field is equally reliable.
Evidence families should be inspectable and bounded.

## Slice 8 - Multi-Source Memory Weighting

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 7
- User stories covered: 6, 13, 26, 27, 28
- Primary goal: distinguish durable taste memory from lightweight session reactions.
- User-facing change: As a user, I will see the app learn more from meaningful repeated behavior and less from one-off weak signals.
- Status: Done locally through source-aware profile concept affinities, relative recency weights, lightweight session-reaction scoring, and repeated-concept tests.

### What to build

Update V2 user-affinity scoring to combine onboarding seeds, Taste Lab ratings, shortlist reactions, watched-history backfill, and post-watch outcomes with source-specific reliability and recency weights.
Post-watch outcomes should outweigh lightweight shortlist reactions, and repeated consistent signals should outweigh one-off weak signals.

### Acceptance criteria

- [x] V2 scoring can identify the source type behind each user evidence contribution.
- [x] Recent post-watch outcomes carry more weight than old weak reactions.
- [x] Shortlist Interested or Maybe or No reactions do not behave the same as watched outcomes.
- [x] Repeated title, keyword, and concept patterns affect ranking more than isolated old signals.
- [x] Evaluation scenarios cover repeated mismatch suppression and high-confidence solo favorites.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when V2 reflects source reliability and freshness in observable ranking behavior.

### Risk notes

Do not create a production-scale learning platform.
This should stay local, inspectable, and fixture-testable.

## Slice 9 - Shared Household Reconciliation Upgrade

- Type: AFK with HITL review if compromise semantics change materially
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 8
- User stories covered: 11, 12, 13, 14
- Primary goal: improve shared ranking while preserving the existing session-mode contract.
- User-facing change: As a couple, we will get recommendations that better balance individual fit, veto risk, shared overlap, and bridge picks.
- Status: Done locally through V2 shared reconciliation evidence, compromise bridge ranking tests, and first-viewer mode tests.

### What to build

Upgrade V2 shared scoring to expose each viewer's independent fit, veto risk, overlap strength, bridge value, and repeated mismatch avoidance.
Keep `husband_first`, `wife_first`, and `compromise` as the active modes while making the underlying shared evidence richer.

### Acceptance criteria

- [x] Shared candidates expose individual fit, overlap strength, veto risk, and bridge value.
- [x] Compromise mode avoids one-sided picks with strong veto risk.
- [x] Husband-first and wife-first modes still visibly favor the selected first viewer without ignoring the second viewer.
- [x] Bridge picks can rise above safe-but-dull middle ground when evidence supports them.
- [x] Evaluation scenarios cover household bridge picks and repeated mismatch suppression.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when shared V2 can explain whether a result is a personal win, compromise win, or bridge win.

### Risk notes

Do not turn session modes into new product modes without founder approval.

## Slice 10 - Confidence, Abstain, And Fallback Ladder

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 9
- User stories covered: 10, 18, 19, 29, 30
- Primary goal: make weak results honest instead of confidently wrong.
- User-facing change: As a user, I will get an honest low-confidence or no-strong-match state when the app cannot find a good enough answer.
- Status: Done locally through V2 confidence assessment, no-strong-match notes, fallback metadata notes, and focused confidence tests.

### What to build

Add V2 confidence output, low-confidence detection, no-strong-match behavior, and a deliberate fallback ladder.
The ladder should handle sparse metadata, over-constrained nudges, time budget pressure, and weak top-candidate separation.

### Acceptance criteria

- [x] V2 can identify when no candidate is a strong match.
- [x] Low confidence produces a product-ready reason and recommended next step.
- [x] Sparse metadata falls back to a simpler safe ranking path.
- [x] Time budget or missing enrichment does not silently fail the recommendation flow.
- [x] Evaluation scenarios verify no-strong-match and fallback behavior.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when V2 can safely step down rather than force a misleading top pick.

### Risk notes

Keep five-title shortlist behavior intact when enough eligible candidates exist.
No-strong-match is about confidence, not watchability eligibility.

## Slice 11 - Debug Evidence And UI Explanation Surface

- Type: AFK with phone-sized UX smoke
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 10
- User stories covered: 9, 14, 17, 30
- Primary goal: make V2 evidence inspectable in debug history and understandable in the results UI.
- User-facing change: As a user, I will be able to understand why a recommendation won, what counted against it, and whether the app only partially understood my request.
- Status: Done locally through V2 snapshot evidence persistence, debug-history payload exposure, result explanation chips, and review-mode phone smoke coverage.

### What to build

Extend debug history and the result explanation surface to show dominant winning reasons, dominant penalties, confidence, fallback status, and partial-support notes.
Keep the UI phone-first and avoid a full redesign.

### Acceptance criteria

- [x] Debug history stores V2 evidence families and fallback state.
- [x] The results UI can show why a title won without exposing internal weight soup.
- [x] Partial-support and low-confidence notes are visible when relevant.
- [x] Existing results flows still render correctly for V1 payloads.
- [x] A phone-sized click-through covers at least one V2 explanation path.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

```sh
pnpm smoke:ux:mobile
```

### Stop condition

Stop when the founder can inspect a V2 recommendation session and understand the main evidence.

### Risk notes

Do not bury evidence only in logs.
Do not redesign the pass-the-phone flow as part of this scoring slice.

## Slice 12 - Live Latency And Phone-Sized Dogfood Gate

- Type: AFK with HITL dogfood review
- Suggested labels: `ready-for-human`
- Blocked by: Slice 11
- User stories covered: 16, 18, 19, 30
- Primary goal: prove V2 is usable in the real couch-flow loop before promotion.
- User-facing change: As a founder, I will be able to try V2 on a phone-sized real flow and judge quality, speed, and trust before making it default.
- Status: Done locally through live TMDb V2 shortlist timing, phone-sized dogfood, and the V1 versus V2 corpus comparison report.

### What to build

Run live TMDb recommendation evaluation and phone-sized pass-the-phone validation with V2 enabled.
Capture recommendation quality, latency, explanation clarity, and visible rough edges.

### Acceptance criteria

- [x] Live TMDb V2 recommendation runs stay fast enough for couch use.
- [x] Phone-sized flow completes setup, preference input, recommendation, results explanation, and follow-up actions.
- [x] The evaluation report compares V1 and V2 on the fixed corpus.
- [x] The dogfood notes identify concrete wins, regressions, and remaining risks.
- [x] Any product decision change discovered during dogfood is classified separately instead of silently folded into the phase.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

```sh
pnpm smoke:ux:mobile
```

### Stop condition

Stop when V2 has both offline evaluation evidence and phone-sized usability evidence.

### Risk notes

A smarter scorer that makes the couch flow feel slow should not be promoted by default.

## Slice 13 - V2 Default Promotion Decision

- Type: HITL
- Suggested labels: `ready-for-human`
- Blocked by: Slice 12
- User stories covered: 16, 19, 20, 30
- Primary goal: decide whether V2 becomes the default scorer.
- User-facing change: As a founder, I will be able to explicitly promote, hold, or revise V2 based on evidence rather than vibes.
- Status: Done locally after founder decision to promote V2 as the default scorer for testing.
- Founder review checklist: [docs/validation/scoring-v2-founder-dogfood-checklist.md](../validation/scoring-v2-founder-dogfood-checklist.md).

### What to build

Prepare the promotion decision package, including evaluation deltas, dogfood notes, latency results, evidence-surface screenshots or summaries, and a rollback plan.
If approved, switch the app default from V1 to V2 while preserving the V1 fallback path.

### Acceptance criteria

- [x] The founder can compare V1 and V2 outcomes on the fixed corpus.
- [x] The promotion decision explicitly records ranking wins, regressions, latency, and fallback behavior.
- [x] V1 remains available as a rollback or fallback path.
- [x] If approved, the default scorer changes in one small reversible commit.
- [x] If not approved, remaining work is moved to a next-phase backlog or risk-closure issue.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

### Stop condition

Stop when the founder has made an explicit promote, hold, or revise decision.

### Risk notes

Do not silently promote V2 just because the implementation exists.
Promotion is a product and trust decision, not only an engineering milestone.

## Dependency Map

```text
Planning Spike - Scoring Data Richness Inventory
  -> 1 Evaluation Corpus And V1 Baseline
  -> 2 V2 Contract And Scorer Selection Flag
    -> 3 Canonical Concept Registry Tracer Bullet
      -> 4 Profile And Candidate Concept Evidence Feed Ranking
        -> 5 Structured Nudge Signals Feed Ranking
          -> 6 Negative Preference Penalties And Honest Partial Support
            -> 7 Metadata Evidence Families For Solo Fit
              -> 8 Multi-Source Memory Weighting
                -> 9 Shared Household Reconciliation Upgrade
                  -> 10 Confidence, Abstain, And Fallback Ladder
                    -> 11 Debug Evidence And UI Explanation Surface
                      -> 12 Live Latency And Phone-Sized Dogfood Gate
                        -> 13 V2 Default Promotion Decision
```

## First Actionable Execution Breakdown

Start with Slice 4.
The Planning Spike and Slices 1 through 3 are complete.
Slice 4 is intentionally profile-and-candidate-first so V2 improves the whole recommender before nudge-specific work.

Immediate implementation checklist:

- Inventory currently available candidate, profile, history, Taste Lab, nudge, and debug fields.
- Check the current TMDb integration for additional fields that are already fetched or could be appended without changing provider strategy.
- Classify each signal by recommendation value, latency risk, cacheability, explainability, privacy sensitivity, and testability.
- Recommend the first V2 evidence families and the deferred data sources.
- Add committed evaluation fixtures for the first seven scenario families from the PRD.
- Add a V1 baseline runner that uses the current scorer and records ranked titles, evidence families, uncertainty, and shortlist count.
- Add assertions that encode expected preference or avoidance behavior at scenario level.
- Generate or document a readable baseline report.
- Run `pnpm check`.

Do not start by changing weights.
Do not start by broadening live candidate generation.
Do not publish GitHub Issues until the founder approves this breakdown and GitHub publication.
