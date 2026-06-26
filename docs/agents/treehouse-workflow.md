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
