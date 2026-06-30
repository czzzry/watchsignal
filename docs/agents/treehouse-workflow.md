# Treehouse Agent Workflow

Treehouse gives autonomous agents isolated reusable Git worktrees.
Use it when two or more agents may work at the same time.

Treehouse does not replace product scoping, issue slicing, GNHF, or host review.
It only gives each worker a clean room.

## Local Setup

Treehouse is installed repo-locally at `.tools/bin/treehouse`.
If the local binary is missing, reinstall it with:

```sh
scripts/install_treehouse.sh
```

The repo config is `treehouse.toml`.
This project uses a project-local worktree pool under `.treehouse/`.
That folder is ignored by Git.

Use this command to check the pool:

```sh
.tools/bin/treehouse status
```

## Agent Run Pattern

Use one leased Treehouse worktree per active worker.
A lease keeps that worktree reserved until the host returns it.

Acquire a worktree:

```sh
.tools/bin/treehouse get --lease --lease-holder issue-2-api
```

Treehouse prints the absolute path of the leased worktree.
Give that path to the worker as its working directory.

Return a worktree after review:

```sh
.tools/bin/treehouse return <worktree-path>
```

## Dependency Prewarm

Treehouse worktrees are isolated from the main checkout.
They do not automatically contain `.tools/uv`, `apps/web/node_modules`, or other local build artifacts.

Before an AFK multi-agent run, the host should either prewarm each leased worktree or give workers explicit commands that point at the main repo's shared caches.

Backend validation can use the main repo's `uv` binary and cache:

```sh
cd apps/api
env XDG_CACHE_HOME=/Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/cache /Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/uv/bin/uv run python -m unittest discover -s tests
env XDG_CACHE_HOME=/Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/cache /Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/uv/bin/uv run python -m compileall -q src tests
```

Web validation should install dependencies in the leased worktree before building:

```sh
env npm_config_cache=/Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/npm-cache PNPM_HOME=/Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/pnpm XDG_CACHE_HOME=/Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/cache npm exec --yes --package=pnpm@10 -- pnpm --dir apps/web install
env npm_config_cache=/Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/npm-cache PNPM_HOME=/Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/pnpm XDG_CACHE_HOME=/Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/cache npm exec --yes --package=pnpm@10 -- pnpm --dir apps/web build
```

This prevents agents from mistaking missing local tooling for product failure.

## Coordination Rules

Each parallel task must define owned files or modules.
Each parallel task must define files or modules that are off limits.
Workers should assume other agents are active.
Workers must not revert unrelated changes.
Workers should commit only their own bounded work.

The host agent reviews each returned worktree before integration.
Treehouse isolation prevents file collisions.
It does not prevent design mismatch.

## Recommended First Multi-Agent Round

Run Issue #2 and Issue #3 in parallel only after Issue #1 is reviewed.

Issue #2 worker owns the backend persistence slice.
Likely owned area: `apps/api`.

Issue #3 worker owns the setup wizard UI slice.
Likely owned area: `apps/web`.

A third worker may prepare TMDb title-resolution fixtures or an implementation brief.
Likely owned area: `docs/`, `apps/api/tests/fixtures/`, or both.

Do not let multiple workers edit the same file unless the host explicitly creates an integration plan.
