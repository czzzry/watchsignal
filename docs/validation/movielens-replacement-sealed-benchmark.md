# Replacement Sealed Model Benchmark

Date: 2026-07-11.
Status: Replacement panel spent exactly once.

## Decision

The founder action is `promote_challenger_as_offline_champion`.
The offline individual-taste champion is `collaborative_challenger`.
Learned eligibility over V2 passed.
The quality route failed.
The simplicity route passed.
The product default remains V2 until separate household evidence authorizes a change.

## Sealed Evidence

The panel contains 5000 previously unused users.
Collaborative challenger NDCG@5 is 0.615832.
Support-aware hybrid NDCG@5 is 0.615439.
V2 NDCG@5 is 0.437816.
Challenger minus V2 NDCG@5 is 0.178017, with a paired 95% interval from 0.171070 to 0.184620.
Challenger minus hybrid NDCG@5 is 0.000393, with a paired 95% interval from -0.001928 to 0.002588.

## Cost And Safety

The challenger artifact is 78.6 percent smaller than hybrid.
The same-loop scoring, fit-time, dislike, coverage, and pairwise gates are recorded in the JSON report.

## Claim Boundary

This is independent-user evidence from the same MovieLens 32M source corpus.
It is not cross-dataset replication and does not prove household compromise, tonight intent, availability, or product adoption.
Any model revision informed by this result requires a fresh independent panel.
