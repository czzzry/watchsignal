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
