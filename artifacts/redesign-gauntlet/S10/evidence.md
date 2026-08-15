# S10 Required onboarding builder evidence

## Claim

Each participating profile can supply the minimum Loved, It was fine, and Not for me evidence in a short private flow rather than a giant form.

## Contract

The three existing onboarding buckets and title-resolution entry shapes remain unchanged.
The save path writes only `onboardingPrompt.profileId`, refreshes backend completion, and opens the next incomplete profile.
Shared mode remains locked until the backend reports every participating profile complete.

## Boundary

`RequiredOnboarding` owns the onboarding Utility presentation and local step navigation.
The existing onboarding state hook owns API loading, draft mutation, profile-scoped saving, completion refresh, and error retention.
Recommendation weights, viewer mappings, private-session architecture, and setup-board design are unchanged.

## Behavior

Every profile enters through a private identity screen, answers one bucket at a time, can search quick poster-led results or add an unresolved title, reviews a compact summary, and can go Back to edit.
The Continue action stays disabled until the active bucket has evidence.
The final save stays disabled until all three buckets are complete and is synchronously guarded against duplicate submission.
The next profile receives a fresh identity screen rather than the previous profile’s selections.

## Evidence

- Focused S10 contract and integration tests: 7 of 7 passing before the full gate.
- Web TypeScript check: passing.
- Real isolated Chrome and a temporary clean API database captured the identity intro and active Loved state at 320, 390, 430, and 390 by 568.
- The real UI showed intentional TMDB poster art for quick results, disabled Continue before selection, complete app/footer isolation, and 44-pixel controls.
- Automated completion traversal did not finish because the scripted quick-result click did not commit during the capture run; summary, next-profile handoff, 200-percent, and active preference-mode capture remain explicit critic gates.

## Decision

Builder handoff only.
Acceptance belongs to the independent critic.
