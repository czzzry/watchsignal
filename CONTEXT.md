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

## Private-transition recovery direction

- Option A durable database recovery is the accepted architecture for API-backed couple sessions.
- R1 strict recovery contracts and durable storage are independently accepted.
- R2 authenticated stateless transport and scheduled cleanup are independently accepted.
- R3 canonical session idempotency, command leases, stale-worker fencing, exact taste-memory side effects, and crash-window reconciliation are independently accepted.
- R4 browser integration, result acknowledgement, and removal of the process-local vault are independently accepted.
- R5 local release evidence passes the full web and API suites, API compilation, TypeScript, the production build, the live 390 by 844 household journey, MVP+4, and MVP+5.
- Publication remains founder-owned because a deployed Vercel and Neon cold-invocation trace and an intentional reviewed Git checkpoint are not local implementation actions.
