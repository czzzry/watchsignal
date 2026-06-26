# movie-night-mediator-app

Code-first prototype repo for a personal Movie Night Mediator.
This project exists alongside the n8n-based repo so we can compare a workflow-first implementation with an app-first implementation.

## Current intent

This repo is for a local mobile web application prototype.
The likely shape is:
- phone-first web UI for couch use
- normal application code for session state and recommendation logic
- stronger separation between interface, application state, persistence, and scoring than the n8n version
- Next.js frontend in `apps/web`
- FastAPI Python backend in `apps/api`
- SQLite as the local MVP source of truth

Telegram remains a possible later adapter.
It is no longer the primary MVP interface for this code-first repo.

## What was carried over

This repo starts with the highest-signal product artifacts from the n8n project:
- founder decisions
- PRD and issue breakdown
- architecture overview
- data dictionary
- scoring-module contract
- decision docs
- Pocock-style agent docs

These documents are inputs, not fixed implementation constraints.
The code-first prototype may evolve the execution architecture while keeping the same product intent.

## Initial direction

The likely next implementation step in this repo is a local mobile web MVP that supports:
1. onboarding
2. shared couple recommendation
3. feedback and outcome capture

The MVP should be usable from two phones on the same couch and local network.
Hosted web and native mobile belong to later notes unless the founder changes that decision.

Pass-the-phone is the first input mode.
Separate-phone participation is a later option unless it comes almost for free.

## Development layout

- `apps/web`: Next.js phone UI
- `apps/api`: FastAPI backend, SQLite persistence, recommendation core, and API contracts
- `docs`: product, architecture, and agent-operating guidance

## Current validation

```sh
cd apps/api
../../.tools/uv/bin/uv run python -m unittest discover -s tests
../../.tools/uv/bin/uv run python -m compileall -q src tests
```

```sh
env PNPM_HOME="$PWD/.tools/pnpm" XDG_CACHE_HOME="$PWD/.tools/cache" npm exec --yes --package=pnpm@10 -- pnpm --dir apps/web build
```

`uv` is installed in a workspace-local helper environment at `.tools/uv`.
`pnpm` can be invoked through `npm exec` without a global install.

## Key docs

- [Founder Decisions](docs/founder-decisions.md)
- [PRD](docs/prd-mvp.md)
- [Architecture Overview](docs/architecture-overview.md)
- [Scoring Module Contract](docs/scoring-module-contract.md)
- [Issue Breakdown](docs/issue-breakdown.md)
- [Code-First App Architecture](docs/architecture/code-first-app-architecture.md)
- [Autonomous Work Protocol](docs/agents/autonomous-work-protocol.md)
