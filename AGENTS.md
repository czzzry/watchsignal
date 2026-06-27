# AGENTS.md

## Project intent

This repo is the code-first companion to the n8n Movie Night Mediator project.
It is intended as a prototype space for building the same core product with application code rather than n8n workflows.
The goal is to compare clarity, maintainability, and recommendation-engine flexibility.

## Decision ownership

The founder or product lead owns final product, architecture, privacy, vendor, and portfolio decisions.
Codex should treat the carried-over docs as product guidance, not as immutable implementation law.

## Codex may

- Create and maintain docs, app scaffolding, schemas, tests, samples, and reversible code structure
- Propose backend architecture, state models, and service boundaries
- Suggest options, tradeoffs, revisit triggers, and validation steps
- Organize repo artifacts to make the code-first comparison easier to inspect

## Standing authorization for routine repo work

Inside this project folder, Codex is pre-authorized to perform routine, reversible repository work.
This includes:
- creating folders and files
- editing docs and source files
- initializing local Git
- running `git status`
- staging files
- making local commits when explicitly requested

Codex should still stop and ask before:
- destructive actions
- deleting files
- force resets or history rewrites
- pushing to a remote
- external network or service changes
- creating, handling, or committing secrets
- introducing paid vendors
- changing architecture or product decisions that require founder approval and an ADR

## Permission request posture

- Keep permission requests minimal and specific
- Surface expected permission needs early before long AFK work
- Batch related permission needs into one request when practical
- Prefer workspace-local installs, caches, and generated files when possible
- Ask before installing persistent user-level or machine-level tools
- Explain whether a request is for network access, external services, filesystem writes outside the repo, or Git publication

## General operating guidelines

- Never use the em dash character and use a plain dash instead
- Never auto-add the agent name as a co-author in commit messages
- Never manually modify `CHANGELOG.md` files or files marked auto-generated
- When writing or substantially editing long Markdown files, put each full sentence on its own line
- Prefer quality, simplicity, robustness, scalability, and long-term maintainability
- For bug fixes, reproduce the bug in an end-to-end setting as closely aligned with the user experience as possible
- Apply the same standard to engineering quality, including lint, test failures, and flaky tests

## Architecture posture

- Prefer boring, reversible, inspectable architecture
- The MVP interface is local mobile web
- Keep Telegram as a later adapter option, not the primary MVP architecture
- Keep recommendation logic separate from transport and orchestration concerns
- Prefer explicit service boundaries over hidden workflow state
- Treat scoring and recommendation logic as code-first in this repo

## UI review posture

- For meaningful mobile UI screens, flows, or design alternatives, use Lavish or another reviewable visual artifact when it helps the founder compare direction
- Do not block tiny UI fixes on Lavish
- Keep UI work phone-first, polished, and pass-the-phone friendly
- For meaningful UI flow changes, perform an actual browser click-through on a phone-sized viewport when practical
- Treat a production build as necessary but not sufficient for UX-facing flow changes
- Capture or summarize what was clicked, what passed, and any visible rough edges after UX validation

## Agent skills

### Issue tracker

Issues are intended to live in GitHub once a remote exists.
See `docs/agents/issue-tracker.md`.

### Triage labels

Use the default five-label triage vocabulary.
See `docs/agents/triage-labels.md`.

### Domain docs

This repo is single-context.
Use the carried-over product docs in `docs/` and ADRs in `docs/adrs/`.
See `docs/agents/domain.md`.

## Skill note

A Pocock-style skill setup has been carried over through the `docs/agents/` structure.
Kun Cheng's GNHF skill has been copied into the local agent skills folder, but autonomous GNHF runs should wait until the repo has bounded issues, validation commands, and clean worktree rules.
See `docs/agents/autonomous-work-protocol.md`.

## End-of-task summary rule

End every substantial task with a plain-English summary covering:
- what changed
- files changed
- decisions touched
- decisions not changed
- validation performed
- open risks
- recommended next step
