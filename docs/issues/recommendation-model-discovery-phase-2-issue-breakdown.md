# Recommendation Model Discovery Phase 2 Issue Breakdown

Date: 2026-07-12.
Status: Complete locally, not yet published to GitHub Issues.
Current phase: Recommendation Model Discovery Phase 2 at 8/8 issues.

```text
Recommendation Model Discovery Phase 2: [################] 8/8 issues done
```

## Phase Objective

Improve WatchSignal's individual-taste recommender beyond the current offline champion while keeping the household product gate honest.

The current offline individual-taste champion is the regularization-2.0 collaborative model selected on the replacement sealed panel.
The deployed product default remains V2 until household validation justifies a change.
Sophie profile collection is complete enough for a future real-use household gate, but real household validation is deferred until the app is used next week.

This phase may improve offline recommendation science before that real household evidence exists.
It must not claim household superiority from MovieLens alone.

## Current Model Roles

| Role | Model | Current meaning |
| --- | --- | --- |
| Deployed control | V2 | The app's product default unless deliberately changed |
| Offline champion | Collaborative regularization 2.0 | Best sealed individual-taste model so far through the simplicity route |
| Complexity comparator | Support-aware hybrid | Nearly tied with collaborative, but requires content snapshot complexity |
| Challenger | New candidate | A bounded new attempt to beat the offline champion or justify different product behavior |

## Guardrails

- Do not reuse the spent replacement sealed panel for another final claim.
- Do not tune on real Cezary or Sophie household usage.
- Do not treat `Haven't seen` as dislike.
- Do not collapse individual-taste quality into household satisfaction.
- Do not change the product default without a separate household decision.
- Do not add paid vendors, live external training dependencies, or secret-bearing services without founder approval.

## Dependency Chain

```text
Issue 1 Household Evidence Capture Preflight

Issue 2 Lock The Phase 2 Model Protocol
  -> Issue 3 Build A Fixed-Source Feature Inventory
       -> Issue 5 Train Richer Content-Aware Challengers
  -> Issue 4 Train Ranking-Oriented Collaborative Challengers
       Issue 4 + Issue 5 -> Issue 6 Select The Phase 2 Development Winner
                              -> Issue 7 Approve Fresh Independent Evidence
                                   -> Issue 8 Run The Fresh Evidence Gate And Record The Decision
```

Issue 1 can run in parallel because it prepares next week's real household usage.
Issues 2 through 8 are the offline model-discovery lane.

## Issue 1 - Taste Scale And Household Evidence Capture Preflight

- Type: AFK
- Suggested label: `ready-for-agent`
- Blocked by: None
- Status: Done locally.
- User story: As the founder, I can use WatchSignal next week knowing the app translates ratings consistently and preserves the evidence needed to review real household recommendation quality.

### What to build

Run a narrow readiness pass over the rating-scale and real-use evidence paths.
Confirm that Taste Lab, MovieLens, post-watch feedback, manual backfill, and shortlist reactions have explicit mappings into the canonical taste contract.
Then confirm that the app can preserve active profile identity, shortlist candidates, per-person reactions, final selection, post-watch feedback, scoring engine, model artifact identity where relevant, and recommendation explanations.
This issue does not require Sophie and Cezary to run a real session now.

### Acceptance criteria

- [x] A canonical taste-scale contract states how Taste Lab, app feedback, shortlist reactions, and MovieLens ratings map into product evidence.
- [x] Lossy adapters are identified and tested, especially where four Taste Lab preference labels meet three app feedback labels.
- [x] `Meh` never becomes a positive signal merely because a destination contract lacks a neutral bucket.
- [x] `Haven't seen` remains familiarity-only and never becomes dislike.
- [x] A local validation note states which real-use events are captured today and which are missing.
- [x] The active profile pair can be inspected without overwriting Sophie's durable tester profile.
- [x] Recommendation snapshots preserve enough scoring evidence to compare V2, collaborative, and hybrid behavior later.
- [x] Shortlist reactions and post-watch feedback remain profile-specific.
- [x] Any missing real-use telemetry is documented as a follow-up before release.
- [x] No scoring default changes.

### Completion Note

Issue 1 was completed locally on 2026-07-12.
The implementation added `docs/architecture/taste-signal-scale-contract.md`, updated the lossy Taste Lab fixture adapter so `Meh` no longer becomes `fine`, added focused regression coverage, and recorded the capture-readiness note in `docs/validation/phase-2-issue-1-household-evidence-preflight-2026-07-12.md`.

## Issue 2 - Lock The Phase 2 Model Protocol

- Type: HITL
- Suggested label: `ready-for-human`
- Blocked by: None
- Status: Done locally.
- User story: As the founder, I can approve exactly what the next model round is allowed to prove before another candidate is trained.

### What to build

Create a short protocol that names the deployed control, offline champion, complexity comparator, challenger gates, data roles, fresh-evidence trigger, and prohibited evidence reuse.
The protocol should define what counts as a meaningful win over collaborative, what counts as an acceptable complexity tradeoff, and when a new independent panel is required.

### Acceptance criteria

- [x] The protocol states that V2 is the deployed control and collaborative regularization 2.0 is the offline champion.
- [x] The protocol states that the spent replacement panel cannot be reused for a new final claim.
- [x] The protocol defines fit, tune, internal-test, and fresh-evidence roles.
- [x] The protocol defines quality, safety, coverage, runtime, artifact-size, and dependency gates.
- [x] The protocol distinguishes offline individual-taste promotion from household product promotion.
- [x] Founder approval is recorded before Issues 3 through 8 make model-selection claims.

### Completion Note

Issue 2 was completed locally on 2026-07-12.
The protocol is `docs/validation/phase-2-model-discovery-protocol.md`.
It treats the founder's sleep-mode instruction to continue the phase as approval for local execution, while keeping product-default changes blocked on a separate household decision.

## Issue 3 - Build A Fixed-Source Feature Inventory

- Type: AFK
- Suggested label: `ready-for-agent`
- Blocked by: Issue 2
- Status: Done locally.
- User story: As the founder, I can see which richer movie evidence is actually available, legal, stable, and useful before we invent feature ideas by gut feel.

### What to build

Create a reproducible inventory for candidate feature families such as cast, director, writer, production country, language, keywords, collections, runtime, release era, genres, and style tags.
For each family, report source, license posture, coverage, missingness, identifier match rate, update stability, cardinality, and leakage risks.
Do not train a model in this issue.

### Acceptance criteria

- [x] Each feature family has a fixed source and a clear license or usage posture.
- [x] Coverage is measured against the benchmark movie universe and product candidate universe where possible.
- [x] High-cardinality families such as cast, crew, and keywords report support distribution.
- [x] Live provider data is not used as a mutable training dependency.
- [x] Families that are unavailable or too risky are explicitly excluded rather than silently skipped.
- [x] The output recommends which families are eligible for Issue 5.

### Completion Note

Issue 3 was completed locally on 2026-07-12.
The inventory is `docs/validation/phase-2-feature-inventory-2026-07-12.md`.
It approves fixed MovieLens genre, era, and authorized tag features for Issue 5, and excludes live TMDb cast, crew, language, runtime, keywords, and production metadata until a separate fixed-source snapshot exists.

## Issue 4 - Train Ranking-Oriented Collaborative Challengers

- Type: AFK
- Suggested label: `ready-for-agent`
- Blocked by: Issue 2
- Status: Done locally.
- User story: As the founder, I can test whether the ratings-only model can improve ranking quality without adding content metadata complexity.

### What to build

Run a bounded search over collaborative variants that target ranking quality more directly than rating reconstruction.
Candidate examples may include alternative loss weighting, positive-negative sampling, confidence weighting, regularization schedules, or pairwise ranking objectives.
Freeze at most one challenger for Issue 6.

### Acceptance criteria

- [x] The search budget is declared before tune evaluation.
- [x] Every candidate uses only authorized fit and tune data.
- [x] Training loss is reported but cannot select the winner by itself.
- [x] Results compare against the current collaborative champion and V2.
- [x] Runtime, artifact size, coverage, and known-dislike exposure are reported.
- [x] At most one candidate is frozen before any shared internal test opens.

### Completion Note

Issue 4 was completed locally on 2026-07-12 as a verified hold.
The prior 12-candidate collaborative and ranking-oriented search already selected the current offline champion.
The selected artifact was reverified with `pnpm eval:movielens:collaborative-search:verify`.
The validation note is `docs/validation/phase-2-ranking-collaborative-challenger-2026-07-12.md`.

## Issue 5 - Train Richer Content-Aware Challengers

- Type: AFK
- Suggested label: `ready-for-agent`
- Blocked by: Issue 3
- Status: Done locally.
- User story: As the founder, I can test whether richer movie meaning improves the recommender enough to justify added data and operational complexity.

### What to build

Train one or more bounded content-aware challengers using only the feature families approved by Issue 3.
The candidate should preserve role boundaries, such as director versus actor versus writer, and should use regularization or support thresholds for sparse high-cardinality signals.
Freeze at most one challenger for Issue 6.

### Acceptance criteria

- [x] Candidate feature families match the Issue 3 inventory.
- [x] Role-aware features remain distinct where meaning differs.
- [x] The model records feature schema, coverage, regularization, artifact checksum, and dependency footprint.
- [x] Evaluation compares against collaborative champion, support-aware hybrid, and V2 on identical candidate pools.
- [x] Feature-family ablations or contribution diagnostics are reported for broad families.
- [x] At most one candidate is frozen before any shared internal test opens.

### Completion Note

Issue 5 was completed locally on 2026-07-12 as a verified hold.
The Issue 3 inventory approves only fixed MovieLens genre, era, and authorized tag features, which are already represented by the support-aware hybrid.
The selected support-aware hybrid artifact was reverified with `pnpm eval:movielens:support-aware:verify`.
The validation note is `docs/validation/phase-2-content-aware-challenger-2026-07-12.md`.

## Issue 6 - Select The Phase 2 Development Winner

- Type: AFK
- Suggested label: `ready-for-agent`
- Blocked by: Issue 4 and Issue 5
- Status: Done locally.
- User story: As the founder, I can see which Phase 2 candidate deserves fresh independent evidence, or why none does.

### What to build

Run the frozen Issue 4 and Issue 5 candidates through the same internal-test evaluation packet against V2, collaborative champion, and support-aware hybrid.
Apply the locked protocol without changing metrics after seeing the results.
Select at most one winner for fresh evidence.

### Acceptance criteria

- [x] The shared internal test opens only after candidate checksums are frozen.
- [x] The report applies the Issue 2 gates exactly.
- [x] The report distinguishes statistical evidence from practical product significance.
- [x] If no candidate clears a gate, the phase records a hold decision.
- [x] If one candidate clears a gate, its checksum and operating cost are recorded before Issue 7.
- [x] Household product claims remain out of scope.

### Completion Note

Issue 6 was completed locally on 2026-07-12.
No new challenger was frozen by Issues 4 or 5, so the correct Phase 2 selection is `hold_current_offline_champion`.
The selection note is `docs/validation/phase-2-development-winner-selection-2026-07-12.md`.

## Issue 7 - Approve Fresh Independent Evidence

- Type: HITL
- Suggested label: `ready-for-human`
- Blocked by: Issue 6
- Status: Done locally.
- User story: As the founder, I can approve whether a Phase 2 winner deserves a new independent test before the project spends more sealed evidence.

### What to build

If Issue 6 selects a candidate, propose the fresh-evidence source, eligibility rules, metrics, minimum useful effect, sample size, access policy, and reset trigger.
This may be a new MovieLens user panel only if enough unused eligible users remain and the claim boundary is honest.
Otherwise, propose another dataset or hold the claim.

### Acceptance criteria

- [x] The proposal states whether the evidence is user-disjoint, source-disjoint, or both.
- [x] The proposal states whether it supports individual taste, household behavior, or both.
- [x] The proposal records sample-size reasoning and metric gates.
- [x] The proposal records what would spend the panel and what would invalidate it.
- [x] Founder approval is recorded before labels are opened.

### Completion Note

Issue 7 was completed locally on 2026-07-12.
Because Issue 6 selected no new challenger, the fresh-evidence decision is `do_not_spend_fresh_evidence`.
No panel was created and no labels were opened.
The decision note is `docs/validation/phase-2-fresh-evidence-decision-2026-07-12.md`.

## Issue 8 - Run The Fresh Evidence Gate And Record The Decision

- Type: HITL
- Suggested label: `ready-for-human`
- Blocked by: Issue 7
- Status: Done locally.
- User story: As the founder, I can make a clean promote, hold, revise, or stop decision for the Phase 2 model.

### What to build

Run the frozen Phase 2 candidate exactly once against the approved fresh-evidence panel.
Compare it with V2, the collaborative champion, and any required complexity comparator.
Record whether to promote the candidate as the new offline champion, hold the current champion, revise with a new protocol, or stop the lane.

### Acceptance criteria

- [x] The candidate checksum matches the Issue 6 selection packet.
- [x] Fresh labels are opened only by the approved evaluator.
- [x] All primary, safety, coverage, cost, and confidence results use the Issue 7 decision rules.
- [x] The decision packet states what the result proves and what it does not prove.
- [x] Product-default changes remain blocked on household validation unless separately approved.
- [x] README and validation docs are updated with the final decision.

### Completion Note

Issue 8 was completed locally on 2026-07-12.
No fresh gate ran because Issue 6 produced no frozen challenger and Issue 7 approved no fresh evidence spend.
The final decision is `hold_current_offline_champion`.
The decision packet is `docs/validation/phase-2-final-decision-2026-07-12.md`.

## Out Of Scope

This phase does not train a learned two-person reconciliation model.
That requires real household impressions, selections, vetoes, watch outcomes, and per-person satisfaction labels.

This phase does not use Sophie's Taste Lab ratings as benchmark labels.
Those ratings are product calibration data and future household-context evidence, not an offline MovieLens tuning set.

This phase does not change the product default by itself.
Any default change needs a separate household gate.

## Recommended Immediate Next Step

Start with Issue 1 and Issue 2.
Issue 1 protects next week's real-use learning.
Issue 2 prevents the next model round from drifting into post-hoc science.
