# Hosted Android Pilot Issue Breakdown

## Phase status

The phase is in local implementation while the final external issue total remains unaccepted.
The founder authorized an AFK run to complete as much reversible local work as possible before live provisioning.

## Locked outcome

The founder can install WatchSignal from Chrome on one Android phone, turn the development computer off, and use the existing product flow against durable hosted data.
Approved changes merged into `main` update the installed app automatically.
The founder's wife can later install the same app and use the same household sequentially.

## Slice 1 - Hosted recommendation tracer

Type: HITL at provisioning, AFK for implementation.
Blocked by: none.

Deploy Next.js and FastAPI from the monorepo and prove one complete fixture recommendation while the development computer is off.
Do not migrate private data in this slice.

## Slice 2 - Installable Android shell

Type: AFK.
Blocked by: Slice 1 only for live-device proof.

Provide a valid Android web manifest, square icons, portrait standalone behavior, safe viewport handling, and a useful disconnected state.

## Slice 3 - Private household access

Type: AFK for implementation and HITL for the real secret.
Blocked by: none for local implementation.

Require a shared household passphrase on hosted web requests, remember approved phones securely, and require a separate token on backend requests.

## Slice 4 - PostgreSQL setup tracer

Type: AFK.
Blocked by: none for local compatibility work and Slice 1 for live proof.

Run household setup and onboarding through PostgreSQL while keeping local SQLite tests unchanged.

## Slice 5 - PostgreSQL couch flow

Type: AFK.
Blocked by: Slice 4.

Persist sessions, shortlist state, reactions, handoff, reranks, snapshots, outcomes, and history through PostgreSQL.

## Slice 6 - PostgreSQL taste evidence

Type: AFK.
Blocked by: Slice 4.

Persist Taste Lab ratings and taste memory through PostgreSQL without changing their scoring meaning.

## Slice 7 - PostgreSQL household memory

Type: AFK.
Blocked by: Slice 4.

Persist watchlist, feedback, watched-title backfill, and remaining household memory through PostgreSQL.

## Slice 8 - Guarded real-data migration

Type: HITL for the real import and AFK for tooling.
Blocked by: Slices 4 through 7.

Back up the local SQLite database, inspect source counts, initialize the hosted schema, import in foreign-key order, and reject any count mismatch.

## Slice 9 - Recoverable free pilot

Type: HITL for a live recovery exercise and AFK for tooling and documentation.
Blocked by: Slice 8.

Prove recovery, deployment rollback, health reporting, and explicit free-tier upgrade triggers.

## Slice 10 - Automatic approved updates

Type: AFK for configuration and HITL for repository and Vercel settings.
Blocked by: Slice 1 for live proof.

Validate pull requests, deploy `main` automatically, expose a build identifier, and prove that a harmless change reaches the installed app.

## Slice 11 - Founder Android acceptance

Type: HITL.
Blocked by: Slices 1 through 10.

Install the app on the founder's actual Android phone and complete the product flow with the development computer off.

## Slice 12 - Wife Android validation

Type: HITL.
Blocked by: Slice 11.

Install the same app on the founder's wife's phone and prove sequential shared-household use without adding simultaneous two-device voting.

## Explicit exclusions

- Google Play publication.
- iPhone support.
- Offline operation.
- Simultaneous two-phone voting.
- Separate user accounts.
- Paid hosting or a custom domain.
- Recommendation-model or scoring changes.
