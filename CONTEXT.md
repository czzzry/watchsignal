# CONTEXT

This repo is a code-first prototype of the Movie Night Mediator product.
The source product intent and decision posture were carried over from the n8n companion project.

## Product identity

- Private household product
- Local mobile web is the MVP interface
- Telegram remains an acceptable later adapter
- Recommendation quality matters more than perfect explainability
- Shared couple decision-making is the core product problem
- Pass-the-phone is the first shared-session input mode
- Separate-phone use is MVP plus N unless it is cheap to add safely

## Architectural direction

- Use normal code for orchestration and recommendation logic rather than n8n workflows
- Keep transport, application state, and scoring logic separable
- Treat current docs as guidance for the prototype, not as a prohibition on cleaner implementation patterns
- Keep this repo fully separate from the n8n project and do not optimize for n8n
- Use Next.js for the phone UI and FastAPI for the backend API
- Use SQLite as the MVP source of truth
- Keep LLM interpretation out of MVP and targeted for MVP plus 1

## Private-transition language

- **Private transition** - The period from the first private movie reaction until the household result is safely displayed.
- **Sealed ballot** - One participant's completed reactions after they have been removed from the shared phone screen.
- **Handoff** - The privacy-safe state in which the phone changes participants and exposes no movie or ballot detail.
- **Recovery** - Resuming an interrupted private transition at a safe state without revealing a prior participant's ballot.
- **Interruption** - A private transition that cannot be recovered safely and must return to a clean start.

## Taste Lens language

- **Taste Lens** - A session-only, explicitly selected source of film-selection signals used to shape one movie-night search. It never changes a household member's durable Taste Lab profile.
- **Curator** - The person whose attributable film selections supply a Taste Lens. A curator is not assumed to have a complete or stable taste profile.
- **Exact list** - A Taste Lens mode that restricts the candidate pool to the curator's attributed selections, then applies household fit, availability, and diversity ranking.
- **Inspiration** - A Taste Lens mode that uses attributable curator selections as retrieval anchors for the wider catalogue. Results must be labelled as inspired by the selections, not as published picks.
- **Browse** - A non-recommendation Taste Lens mode that shows attributable selections without household ranking.
- **Source provenance** - The publisher, URL, date or version where known, signal meaning, rank meaning, and reuse status attached to a curator selection.
- **Eligible selection** - An attributed selection that has a normalized movie identifier, remains unseen for the requested household context, and satisfies the current availability and hard constraints.
- **Permission-cleared catalogue** - A catalogue whose selected titles may be stored and presented in the product under an affirmative license, written permission, or direct rightsholder provision. Public visibility alone is not permission to ingest.

## Private-transition recovery direction

- [ADR-002](docs/adrs/ADR-002-private-transition-recovery.md) owns the selected recovery architecture, privacy, retention, and rollback contract.
- The [redesign acceptance matrix](docs/redesign-gauntlet/acceptance-matrix.md) owns slice status, and the [release checkpoint](docs/validation/watchsignal-redesign-release-checkpoint-2026-08-14.md) owns validation and publication status.
