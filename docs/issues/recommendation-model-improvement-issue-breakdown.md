# Recommendation Model Improvement Issue Breakdown

Date: 2026-07-11.
Status: Complete.
Current phase: Complete at 5/5 issues.

## Phase Objective

Launch the strongest evidence-backed individual taste model behind the existing household decision layer and establish a repeatable champion-challenger system for future improvement.
The regularization-2.0 collaborative challenger is the replacement-sealed offline champion, hybrid is the retained complexity comparator, and V2 is the current deployed control.

This phase does not train a learned two-person reconciliation model.
Issue #127 first combines learned individual taste scores through explicit household and tonight-intent logic and collects real household evidence.
A learned household model requires actual shared-decision and satisfaction labels rather than synthetic MovieLens pairings.

## Dependency Chain

```text
#127 Integrate the approved taste model and pass the household gate
  -> #128 Lock the model improvement development protocol
       -> #129 Learn the support-aware hybrid blend
       -> #130 Train stronger collaborative and ranking candidates
            #129 + #130 -> #131 Select the next development winner
                              -> #132 Create and spend a replacement sealed panel
```

## Accepted Issues

### #128 Lock The Model Improvement Development Protocol

Delivery mode: HITL.
Blocked by: #127.
Lock model roles, development partitions, metrics, practical thresholds, data inventory, leakage boundaries, experiment records, and replacement-seal conditions before training another candidate.
The approved protocol is `docs/validation/model-improvement-development-protocol.md`.

### #129 Learn The Support-Aware Hybrid Blend

Delivery mode: AFK.
Blocked by: #128.
Test whether learned or systematically tuned blending can preserve the hybrid's sparse-item advantage across the broader population.

### #130 Train Stronger Collaborative And Ranking Candidates

Delivery mode: AFK.
Blocked by: #128.
Run a bounded ratings-only search over collaborative capacity, regularization, iterations, and ranking-oriented objectives without selecting from training loss alone.

### #131 Select The Next Development Winner

Delivery mode: AFK.
Blocked by: #129 and #130.
Choose at most one challenger through an unchanged internal-test pipeline, or retain hybrid when no candidate clears the locked gates.

### #132 Create And Spend A Replacement Sealed Panel

Delivery mode: HITL.
Blocked by: #131.
Approve and generate new independent evidence only after a frozen development winner exists, then run it exactly once against hybrid, collaborative, and V2.

## Explicit Next-Phase Backlog

Richer cast, director, writer, language, keyword, and production features are not silently included in this accepted phase.
They require a fixed-source, licensing, coverage, and leakage contract before becoming a separate vertical slice.

A learned two-person reconciliation model is also outside this phase.
It becomes scientifically defensible only after WatchSignal has enough consented household impressions, selections, vetoes, watch outcomes, and per-person satisfaction evidence to define labels and estimate useful sample requirements.

## Completed Outcome

Issue #129 selected support-aware hybrid shrinkage `80` without opening the internal test.
Issue #130 selected the 16-dimension, regularization-2.0 collaborative challenger from 12 predeclared candidates without opening the internal test.
Issue #131 opened the shared internal test once and selected collaborative through the simplicity route rather than the 0.02 quality route.
Issue #132 locked 5,000 previously unused users, spent the replacement panel once, and confirmed the same decision.
The collaborative challenger is now the offline individual-taste champion and the reversible `v2_collaborative` adapter targets its exact checksum.
The product default remains V2 until the separate household gate has enough real evidence.
