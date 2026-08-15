# WatchSignal Redesign Release Checkpoint

Date: 2026-08-14.

Phase: Complete mobile redesign and durable private-transition recovery.

Local slice status: 22 of 23 accepted.

## Purpose

This inventory defines the intended local checkpoint before any commit, push, pull request, or deployment.

It does not authorize publication.

## Included product scope

- The complete phone-first WatchSignal setup, private reaction, handoff, matching, result, utility, Taste Lab, history, login, setup, and credits experience.
- The Cinema, Utility, and Transition visual system and its responsive and accessibility behavior.
- Durable API-backed couple recovery through the strict `PrivateTransitionRecovery` module.
- Stateless authenticated browser-to-API recovery transport.
- PostgreSQL and SQLite recovery persistence, command leases, fencing, reconciliation, expiry, cleanup, and safe consume behavior.
- Shared-session idempotency and exact taste-memory side effects.
- Public error quarantine, review-only diagnostics, route quarantine, and consumer-safe result explanations.
- The generated web API contract and all source tests required by the accepted slices.
- The final mobile dogfood runner and MVP+4 and MVP+5 acceptance reports.
- ADR-002, the recovery implementation gate, product contract, acceptance matrix, status board, and retained visual evidence.

## Intended evidence scope

The redesign evidence directory contains the accepted slice captures, masked comparisons, browser traces, scorecards, and recovery proofs.

These artifacts are intentional review evidence, not runtime dependencies.

The prototype routes are retained as review fixtures but are quarantined from production by the explicit production route policy.

## Explicit exclusions

- `.env` and every non-example environment file.
- Local databases, build outputs, package caches, and dependency directories.
- `.playwright-cli/` browser snapshots and console logs.
- Any active browser profile, preview server state, or temporary API data.
- `docs/expanded-recommender-signal-research-scan.md` until its separate research task decides whether to publish it with this branch.
- Deployment configuration changes in Vercel or Neon.
- Secrets, tokens, connection strings, and household data.

## Current validation

- Tooling tests: 5 of 5 passed.
- Web state tests: 252 of 252 passed.
- API tests: 418 passed with seven hosted-only tests skipped in the ordinary suite.
- API compilation passed.
- TypeScript passed.
- Production build passed with 36 generated pages.
- Hosted PostgreSQL multi-process and crash-window tests: 7 of 7 passed.
- Hosted and beta preflights passed with configuration and dirty-worktree warnings only.
- MVP+4 passed.
- MVP+5 passed.
- The live 390 by 844 complete household journey passed.
- S06 earned independent ACCEPT at 37 of 40 with Functional fidelity at 5 of 5.
- S07 earned independent ACCEPT at 36 of 40 with Functional fidelity at 5 of 5.
- `git diff --check` passed.
- Candidate-checkpoint credential scanning found no credential-shaped value; the only match was the preflight script checking that required variable names exist in `.env.example`.
- The largest individual untracked evidence image is under 1.9 MiB, and no untracked file requires a large-file exception.

## Remaining release evidence

The configured Vercel and Neon pilot must seal recovery on one deployed version or cold invocation and resume it after a fresh deployed invocation without duplicating canonical session or taste-memory writes.

The deployed trace must record only non-sensitive operation, stage, outcome, timing, and aggregate cleanup evidence.

The founder must approve the exact local checkpoint before a commit is created.

The current `codex/implement-cinematic-pulse` branch is already associated with merged pull request 148 and is zero commits ahead of its upstream before these uncommitted changes.

After approval, create a new `codex/watchsignal-redesign-release` branch and commit only the intended scope described here.

The no-mistakes pipeline can then review the committed branch, run its configured gates, and prepare a pull request without silently publishing unrelated files.

## Resource posture

Heavy validation runs are serialized and use reduced process priority.

Every task-owned preview server, browser automation session, test watcher, and build process must be stopped at each pause.

No task-owned process remains active at this checkpoint.

## Decision

The local implementation is ready for a founder-approved checkpoint.

Production release remains held for the deployed Vercel and Neon proof and publication approval.
