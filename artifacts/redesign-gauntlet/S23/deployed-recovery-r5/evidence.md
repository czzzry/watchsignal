# S23 deployed recovery evidence

## Claim

The production WatchSignal pilot can seal a private handoff on one Vercel deployment and restore the safe handoff after a fresh deployment while Neon remains the durable recovery store.

## Contract

The browser checkpoint contains only `version`, `recoveryToken`, and `expiresAt`.

The restored handoff must not expose the first participant's movie titles or reactions.

## Boundary

The browser owns only the opaque checkpoint.

The stateless Vercel web and API functions forward authenticated recovery commands.

Neon owns the durable recovery record.

## Pre-redeployment evidence

- Production merge commit: `72d3e7190c99a2d8195dcab8166f55b48c3d1e83`.
- Production web: `https://watchsignal-web.vercel.app`.
- Production API: `https://watchsignal-api.vercel.app`.
- Both production deployments reported success for the merge commit.
- A signed-in 390 by 844 production journey reached Cezary's first private pass and completed all five reactions.
- The app reached the static `Ready for Husband` handoff.
- Session storage contained `watchsignal.private-transition.v1` with exactly `expiresAt`, `recoveryToken`, and `version`.
- The checkpoint serialized to 101 bytes and exposed no session, household, profile, movie, title, score, stage, or ballot field.
- The live accessibility snapshot exposed only the safe handoff heading and action, with no first-pass movie title or reaction.

## Cross-deployment evidence

The docs-only deployment-trigger merge produced fresh production web and API deployments.

The first resume request reached the fresh web deployment and returned `503` with the fixed public message `Private transition recovery is not configured.`

The response used `Cache-Control: no-store`, left the opaque checkpoint intact, and exposed no token, title, reaction, or server detail.

Production authentication and ordinary API-backed setup requests remained healthy.

The missing requirement was the non-secret `WATCHSIGNAL_HOUSEHOLD_ID` deployment tenant in the web project.

The follow-up deployment config sets `default-household` in the version-controlled Vercel function environment and adds a normalized configuration regression.

The corrected production deployment completed successfully for merge commit `45dc336`.

A new signed-in 390 by 844 journey then completed all five first-pass reactions on that corrected deployment.

The production seal request returned `200` and the production resume reconciliation request returned `200`.

The app reached `Ready for Husband` with no first-pass title or reaction visible.

Session storage again contained only a 101-byte `watchsignal.private-transition.v1` checkpoint with exactly `expiresAt`, `recoveryToken`, and `version`.

This fresh checkpoint was intentionally parked at the safe handoff while one more production deployment was created.

The production web and API deployments completed successfully for merge commit `4659dd4e41e2873046b09ae5610cba8a0407ae32`.

Reloading the same parked 390 by 844 browser tab issued `POST /api/private-transition-recovery/resume`, which returned `200` from the fresh deployment.

The restored screen was exactly `Ready for Husband` and exposed no first-pass movie title or reaction.

Selecting `Begin Husband's picks` opened a clean second private pass at movie 1 of 5.

All five second-pass reactions completed and the app advanced through `Saving your picks` to the ranked five-title result.

The result mounted with `Disclosure Day` ranked first at match score 83, while the recovery network sequence completed with a `204` response from `DELETE /api/private-transition-recovery/consume`.

After result mount, session storage no longer contained `watchsignal.private-transition.v1`; only the non-sensitive launch-sting marker remained.

The deployed result also passed these interaction checks:

- Details opened as a modal and Escape returned focus to the exact `Details` button.
- Selecting the second ranked title changed the active result to `Masters of the Universe`.
- Find five more opened the continuation modal and Escape returned focus to the exact invoking control.
- Result options opened the existing shared watchlist and After tonight utility surfaces.

The browser screenshot command reported a path but did not leave a file on disk, so this evidence does not claim a new retained PNG.

The live accessibility snapshots and sanitized network/status observations are the retained deployed proof for this round.

## Decision

Promote the deployed recovery gate for independent review.

The required cross-deployment resume, second pass, matching, result mount, and consume checks passed on the production Vercel and Neon boundary.
