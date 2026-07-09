# WatchSignal for mika

## What this project is

WatchSignal is a code-first prototype for a tricky real-world coordination problem: helping two people choose a movie together without turning the night into a negotiation spiral.
On the surface it is a movie-night product.
Underneath, it is a working example of how I like to build AI-adjacent systems: explicit contracts, inspectable behavior, evaluation hooks, and agent-friendly boundaries.

This repo started as a companion to an n8n-based concept.
I used it to reframe the same product as normal application code so the recommendation logic, product decisions, and validation flow could be easier to reason about, test, and evolve.

## Why I think it is relevant to mika

The part I am most proud of is not just that I built a prototype.
It is that I structured the work so humans and agents can both contribute without the system turning opaque.

That meant:

- separating UI, API, application services, scoring, storage, and external adapters,
- keeping recommendation logic code-first and replaceable rather than hidden inside workflow glue,
- writing validation gates and smoke flows so changes can be checked against real behavior,
- documenting decision boundaries so iteration stays fast without losing shared context,
- and building recruiter-facing demo surfaces without faking the actual product core.

I think that maps closely to the kind of AI tooling work that matters in practice.
Useful agent systems are not just model calls.
They are operating systems for iteration, trust, debugging, and collaboration.

## System shape

The current stack is a Next.js phone-first frontend, a FastAPI backend, SQLite persistence, TMDb candidate sourcing, and a Python recommendation core.
The product flow is deliberately inspectable: setup, pass-the-phone reactions, shortlist generation, shared recommendation, outcome capture, feedback, and debug evidence all have explicit surfaces in code and docs.

The recommendation layer is intentionally modular.
Scoring is separate from transport and persistence.
Taste calibration data can feed the scorer without becoming a hidden black box.
That made it possible to add a private Taste Lab route, evaluate whether calibration changed rankings, and expose recommendation evidence back to the UI.

## What demonstrates how I work

### 1. I make behavior legible

The repo does not stop at “here is the result.”
It captures why the result happened.
Recommendation snapshots, debug history, evidence drawers, and acceptance-gate writeups all make it easier to inspect the system after the fact.

### 2. I build evaluation loops early

I added deterministic recommendation-evaluation commands and acceptance gates instead of waiting for a future polish pass.
The goal was not to overclaim model quality.
The goal was to create repeatable checks before changing ranking behavior or product flows.

### 3. I design for agent collaboration, not just solo coding

The repo includes explicit docs for agent worktree isolation, bounded ownership, and coordination rules.
That is the kind of scaffolding that makes autonomous or semi-autonomous work safer and more useful.

### 4. I care about product clarity as much as technical correctness

The repo includes a recruiter-facing showcase route and demo assets, but they sit alongside the real application structure, not instead of it.
I want the presentation layer and the underlying system to agree with each other.

## A few concrete proof points

- The architecture is documented in `docs/architecture/code-first-app-architecture.md`.
- Shared recommendation behavior is explained in `docs/architecture/mode-aware-shared-scoring.md`.
- The repo includes a real evaluation harness in `docs/setup/taste-lab-evaluation.md`.
- Validation is tracked through acceptance-gate documents such as `docs/validation/live-usable-mvp-gate-2026-06-30.md` and `docs/validation/mvp-plus-5-acceptance-gate-2026-07-07.md`.
- Agent coordination is documented in `docs/agents/treehouse-workflow.md`.
- The project also includes a recruiter-facing product showcase in `apps/web/app/showcase/page.tsx`.

## What I learned from building it

I learned that the most valuable AI-adjacent systems are the ones that stay understandable under iteration.
It is easy to produce something that looks smart in a demo.
It is much harder, and more useful, to build a system where product behavior, evaluation, and agent contribution all stay visible.

That is the kind of work I want to keep doing.
I want to help build tools and workflows that make agents genuinely reliable teammates for product and engineering teams.
