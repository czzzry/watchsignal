# Phase 2 Model Discovery Protocol

Date: 2026-07-12.
Phase: Recommendation Model Discovery Phase 2.
Issue: 2 - Lock The Phase 2 Model Protocol.
Decision owner: Founder.
Status: Approved for local execution by the founder instruction to continue the phase while sleeping.

## Objective

Find whether WatchSignal can improve the current offline individual-taste champion without weakening the product's scientific boundary.
The phase may produce a new offline champion.
It may not change the product default without separate household validation.

## Model Roles

| Role | Model | Decision question |
| --- | --- | --- |
| Deployed control | V2 | Does a learned model still materially beat what the app currently uses? |
| Offline champion | Collaborative regularization 2.0 | Does a challenger beat or defensibly replace the current best offline individual-taste model? |
| Complexity comparator | Support-aware hybrid | Does added content complexity earn its operating cost? |
| Challenger | New candidate | Does a bounded Phase 2 model clear the locked gates? |

The deployed control and the offline champion are separate.
Beating V2 is necessary for product consideration, but it is not enough to replace the offline champion.

## Evidence Roles

| Evidence role | Allowed use | Claim boundary |
| --- | --- | --- |
| Development fit | Train model parameters | No selection claim |
| Development tune | Select bounded candidate configurations | No final claim |
| Internal test | Select at most one Phase 2 winner | Development evidence only |
| Fresh evidence | Confirm or reject the frozen winner | Only valid once approved and spent |
| Real household use | Product-default review | Not used to tune MovieLens models |

The spent replacement sealed panel cannot be reused for another final claim.
Any model revision influenced by that result requires fresh independent evidence before a new confirmatory claim.

## Gate One: Learned Eligibility Over V2

A Phase 2 challenger must remain eligible against V2 before it can be considered for product integration.
The established-user primary internal test must show:

- NDCG@5 improves over V2 by at least `0.02` absolute.
- The paired 95 percent NDCG@5 interval has a lower bound above zero.
- Pairwise preference accuracy does not regress.
- Known-dislike rate@5 does not regress by more than `0.01` absolute.
- Coverage is at least `0.98`.

This gate asks whether learned individual taste is still materially better than the deployed heuristic.
It does not select among learned models.

## Gate Two: Offline Champion Selection

A challenger may replace the collaborative regularization-2.0 champion through one of two routes.

### Quality Route

Use this route when the challenger has comparable or greater operating complexity than collaborative.

- NDCG@5 improves over collaborative by at least `0.02` absolute.
- The paired 95 percent NDCG@5 interval has a lower bound above zero.
- Pairwise preference accuracy does not regress.
- Known-dislike rate@5 does not regress by more than `0.01` absolute.
- Coverage is at least `0.98`.

### Simplicity Or Operating-Cost Route

Use this route only when the challenger materially reduces a declared cost.

- Challenger-minus-collaborative NDCG@5 lower bound is no worse than `-0.005`.
- Pairwise preference accuracy and known-dislike safety do not regress beyond guardrails.
- Coverage is at least `0.98`.
- At least one declared cost dimension improves by at least 25 percent.
- No other declared cost dimension worsens by more than 25 percent without founder approval.

Allowed cost dimensions are training runtime, scoring runtime, peak memory, artifact size, feature-snapshot size, external data dependence, and operational service dependence.

## Search Budgets

Issue 4 may evaluate at most 12 ranking-oriented collaborative candidates on tune data.
Issue 5 may evaluate at most 12 richer content-aware candidates on tune data.
Each issue may freeze at most one candidate before Issue 6 opens the shared internal test.

Training loss is diagnostic.
It cannot select the model by itself.

## Feature And Data Boundaries

Issue 3 must approve feature families before Issue 5 trains with them.
Features need fixed provenance, license posture, coverage, missingness, cardinality, update stability, and leakage review.
Live provider calls may be used for product candidate generation, but not as mutable training data for this phase.

Sophie's Taste Lab ratings are product calibration data and future household-context evidence.
They are not offline benchmark labels.

## Fresh Evidence Trigger

Issue 7 remains blocked unless Issue 6 freezes exactly one winner that passes the protocol gates.
Fresh evidence must define whether it is user-disjoint, source-disjoint, or both.
It must also define sample size, metrics, access policy, reset trigger, and claim boundary before labels open.

Issue 8 may run the frozen winner once.
If the run fails, the phase records hold, revise, or stop.
It must not change model, metric, or threshold after seeing the result.

## Product Boundary

Passing Phase 2 can identify a new offline individual-taste champion.
It does not prove household compromise quality.
It does not prove tonight-intent quality.
It does not prove streaming availability satisfaction.
It does not authorize a product-default change.

The product default remains V2 until a separate household validation decision changes it.

## Engineering Evidence Loop

Claim: Phase 2 can search for a better individual-taste model without reusing spent sealed evidence or confusing offline quality with household product success.

Contract: The protocol separates deployed control, offline champion, complexity comparator, challenger, data roles, gates, and fresh-evidence rules.

Boundary: Offline model discovery owns individual taste.
Household validation owns product-default promotion.
Real household use is not offline training data.

Behavior: Issues 3 through 8 must follow the locked gates, search budgets, and evidence roles.

Evidence: Prior replacement-sealed results identify collaborative regularization 2.0 as the offline champion and mark the panel spent.
Issue 1 confirms the app can preserve real-use evidence later.

Decision: Proceed to Issue 3 and Issue 4 preparation under this protocol.
