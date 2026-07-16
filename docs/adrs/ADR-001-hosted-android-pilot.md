# ADR-001 Hosted Android Pilot

## Status

Accepted on 2026-07-16 by the founder.

## Context

WatchSignal currently runs as a phone-first Next.js interface backed by a local FastAPI process and SQLite database.
The founder wants an Android-installed app that works while the development computer is off and receives approved fixes automatically.
The first acceptance gate prioritizes one founder-owned Android phone.
A later validation checks the same shared household from the founder's wife's Android phone.
Google Play distribution, offline operation, simultaneous two-phone voting, and separate accounts are not required for this pilot.
The founder already has a Vercel account and prefers a free starting point.

## Decision

Use an installable Progressive Web App delivered through Chrome rather than a Google Play package.
Host the Next.js app and FastAPI API as separate Vercel projects from the existing monorepo.
Use Neon PostgreSQL through `DATABASE_URL` for hosted persistence while retaining SQLite for local development and tests.
Protect the public web app with one shared household passphrase and a secure long-lived session cookie.
Protect the API with a separate server-to-server token and route browser requests through the authenticated Next.js application.
Deploy production automatically from `main` after pull-request validation.
Use Vercel Hobby and Neon Free for the pilot, with explicit upgrade triggers rather than assuming free-tier reliability.

## Options considered

- Keep hosting on the development computer through Tailscale.
- Use paid Render services and managed Render PostgreSQL.
- Publish native Android packages through Google Play.
- Use Vercel Hobby and Neon Free for the first hosted pilot.

## Tradeoffs

The selected option satisfies the computer-off and automatic-update outcomes without an initial hosting bill.
It introduces two external providers and free-tier quotas.
Vercel's Python runtime is currently a deployment risk that must be proven with the real FastAPI application before private data is migrated.
Neon can scale down when idle, so the first request can be slower than a continuously running paid service.
The PWA requires internet and does not provide Play Store discovery or remote installation.

## Reversibility

Medium.
The PWA remains ordinary Next.js code and the API remains ordinary FastAPI code.
PostgreSQL is portable to another managed provider.
The provider-specific work is limited to configuration, environment variables, and deployment runbooks.

## Revisit triggers

- Free-tier cold starts make normal movie-night use frustrating.
- Vercel Python cannot run the application within function limits.
- Neon storage or compute approaches its free allowance.
- Recovery needs exceed the free restore window.
- The app becomes public or commercial.
- Separate accounts, simultaneous devices, or Play Store distribution become product requirements.

## Consequences

SQLite remains the local inspection and test store.
Hosted persistence must use PostgreSQL and must be validated across every existing storage path.
Private local data must be backed up before migration and must never enter Git.
The first live provisioning and real-data import require founder participation.
Recommendation scoring, candidate rules, and the pass-the-phone state machine do not change under this decision.

## Sources

- Founder decisions in the 2026-07-16 Hosted Android Pilot conversation.
- Existing code-first architecture and beta-readiness documents.
- Vercel Next.js and FastAPI deployment documentation.
- Neon PostgreSQL plan and recovery documentation.
