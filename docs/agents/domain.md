# Domain docs

How the engineering skills should consume this repo's domain documentation when exploring the project.

## Layout

This is a single-context repo.

Use these docs when they exist:

- `CONTEXT.md` at the repo root for domain language and glossary guidance
- `docs/adrs/` for architectural decisions and decision history
- decision and research docs under `docs/` when they are relevant to the current task

## Current repo note

There is no `CONTEXT.md` yet.
That is acceptable.
Skills should proceed using the existing planning and decision docs until a dedicated context file is created.

## Vocabulary rule

When naming concepts in PRDs, issues, tests, or architecture notes, use the project's existing decision vocabulary.
Prefer the language already established in:

- `docs/founder-decisions.md`
- `docs/decision-register.md`
- `docs/workflow-map.md`
- `docs/architecture-overview.md`

## ADR rule

When a task touches an architectural area with an ADR, read the relevant ADR first.
If a proposal conflicts with an ADR, surface that conflict explicitly instead of silently overriding it.
