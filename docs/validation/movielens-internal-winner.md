# Model Improvement Internal-Test Winner

Date: 2026-07-11.
Status: Internal development test opened once.

## Decision

The selected development winner is `collaborative_challenger`.
Learned eligibility over V2 passed.
The quality route failed.
The simplicity route passed.
A replacement sealed panel is unblocked.
The product default remains unchanged pending separate household evidence.

## Headline Evidence

Collaborative challenger minus V2 established NDCG@5 is 0.175110, with a paired 95% interval from 0.166784 to 0.183153.
Collaborative challenger minus support-aware hybrid established NDCG@5 is 0.000449, with a paired 95% interval from -0.002967 to 0.003682.

## Cost Evidence

The collaborative challenger reduces artifact size by 78.6 percent.
It removes the fixed content-snapshot dependency and is compared on the same internal windows.

## Evidence Boundary

This is reused-population internal development evidence, not independent final proof.
The result evaluates one-person chronological ranking and does not establish household compromise quality.
