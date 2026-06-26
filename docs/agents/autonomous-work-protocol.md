# Autonomous Work Protocol

This repo is intended to support bounded autonomous agent work.
The goal is to discover how much useful implementation can be delegated without the founder babysitting every step.

## Current Method Decision

Use ordinary Codex work first.
Use Pocock-style skills for grilling, issues, TDD, triage, and diagnosis when they fit.
Use Kun Cheng tools only after the work is scoped tightly enough that autonomous agents have safe rails.
Use Lavish for meaningful mobile UI screens, flows, or design alternatives when a reviewable visual artifact would help the founder compare direction.
Do not block tiny UI fixes on Lavish.

## Tool Roles

Treehouse is worktree infrastructure.
It helps agents work in isolated reusable worktrees.
It does not define the product plan.

GNHF is an autonomous iteration runner.
It can run agents for bounded objectives and commit small successful iterations.
Use it only when a task has clear acceptance criteria and validation commands.

Autopreso is a realtime speech-to-presentation and whiteboard tool.
It is not part of the Movie Night Mediator MVP build.
It may be useful later for explaining architecture or turning a spoken walkthrough into a visual artifact.

No-mistakes is a validation gate.
Use it later when the repo has a branch, committed changes, and enough tests or lint commands to make the gate meaningful.

## Product Scope Agents Must Preserve

- This repo is separate from the n8n project.
- Do not optimize for n8n.
- Do not write into the n8n repo.
- Do not let this implementation alter n8n project decisions.
- Use only this repo as working project context.
- Treat carried-over docs as source material, not as immutable code constraints.
- Do not reopen settled product decisions unless there is a true contradiction or missing decision.
- The MVP interface is local mobile web.
- The MVP must support the shared couple use case.
- Pass-the-phone is the first MVP input mode.
- Separate-phone use is MVP plus N unless it is cheap to add safely.
- The selected stack is Next.js frontend, FastAPI backend, and SQLite persistence.
- LLM interpretation is MVP plus 1, not MVP.
- Solo-only behavior may be used as an engineering tracer bullet, but it is not the MVP.

## Agent-Ready Work Requirements

Before assigning a task to an autonomous agent, define:

- objective
- owned files or modules
- files or modules that are off limits
- accepted product decisions
- open decisions the agent may surface
- acceptance criteria
- validation commands
- expected summary format
- expected learning artifact, when the task changes architecture, product behavior, or workflow

Tasks should be small enough that a successful agent can complete, validate, and summarize the work in one pass.
Tasks should avoid touching the same files as another active agent unless there is an explicit integration plan.

## Learning Artifacts

The founder wants maximum autonomous progress, not frequent teaching interruptions.
Agents should avoid stopping mid-task to explain concepts unless a founder decision is truly required.

When a task materially changes how the product works, the agent should leave behind concise learning support after the work is complete.
Good learning artifacts include:

- a short summary of what changed and why
- a small diagram for new flows, boundaries, or state transitions
- notes on tradeoffs and alternatives rejected
- examples of how to run or inspect the new behavior
- plain-English explanation of new concepts introduced by the task

Learning artifacts should be close to the work.
Use existing docs when appropriate.
Create a new doc only when the explanation would otherwise clutter implementation files.

Do not let documentation become a substitute for working software.
The primary output is still implemented, validated product behavior.

## Recommended Workstream Boundaries

- mobile web UI
- API and session endpoints
- recommendation and scoring core
- persistence adapter
- shared-session state machine
- fixture and synthetic data
- tests and evaluation harness
- docs and issue slicing

## Validation Baseline

Current validation commands:

```sh
cd apps/api
../../.tools/uv/bin/uv run python -m unittest discover -s tests
../../.tools/uv/bin/uv run python -m compileall -q src tests
```

```sh
env npm_config_cache="$PWD/.tools/npm-cache" PNPM_HOME="$PWD/.tools/pnpm" XDG_CACHE_HOME="$PWD/.tools/cache" npm exec --yes --package=pnpm@10 -- pnpm --dir apps/web build
```

Update this list when the web app, frontend tooling, linting, or persistence tests are added.

## GNHF Readiness Gate

Do not run GNHF on broad goals such as "build the app."
Use it for bounded goals such as:

- add persistence tests for shortlist reactions
- implement one API endpoint and tests
- add one mobile screen from an accepted design
- refactor scorer weights while preserving contract tests

A GNHF task is ready when:

- the target branch or worktree is clean
- the task has a narrow file ownership boundary
- validation commands exist
- the stop condition is explicit
- the expected commit behavior is acceptable

## Treehouse Readiness Gate

Use Treehouse when multiple agents need isolated worktrees.
Do not use it as a substitute for issue slicing.
Each Treehouse task still needs a narrow objective and validation command.

## End-of-Task Summary

Autonomous agents should finish with:

- what changed
- files changed
- validation performed
- learning artifact added or updated
- decisions touched
- decisions not changed
- open risks
- recommended next step
