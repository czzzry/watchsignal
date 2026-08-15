# WatchSignal redesign acceptance matrix

The current phase is **Full-product redesign gauntlet: 23/23 slices accepted**.
Each row is deliberately small enough to build, inspect, judge, and revise independently.
S23 passes the startup, public-error, route-boundary, footer, responsive, truthful-onboarding, confirmed-intent, superhero-avoidance, live-result, reaction-copy, outcome-transaction, private-recovery, complete two-person production journey, build, and focused behavior-test gates.
S06 and S07 use the accepted durable database-recovery decision, while local-only rounds use the accepted interruption containment path.

Both choices now have independently reviewed, implementation-ready gates: durable database recovery preserves API-backed couple refresh recovery, while safe restart removes that promise and explicitly abandons or excludes interrupted sessions without revealing a ballot.

| ID | Slice | Primary states and proof | Highest regression risk |
| --- | --- | --- | --- |
| S01 | Design tokens and reusable primitives | Tokens, type, spacing, icons, safe areas, focus, reduced motion, and representative Cinema and Utility harnesses | Broad global styling breaks prototypes or overlays |
| S02 | Golden ranked result | Winner plus four alternatives, active switching, score and gap, reason, Details, Watch, 5 more, missing-art fallback | Production lacks backdrop data and current result is long-form |
| S03 | Result details and availability | Synopsis, three cast members, reasons, provider access, close and focus return, fallback states | Cast is unstructured and Watch has no launch URL |
| S04 | Private reaction card and movie information | Compact card, details, Interested, Maybe, No, back, sync-disabled state, missing data | Optimistic delay and async write can duplicate or skip a vote |
| S05 | Seen-before memory | Loved, Ok, Hated, I forget, save warning, return to tonight reaction | Memory can save against the wrong profile or look like a vote |
| S06 | Private sealing and handoff | Ballot seal, privacy promise, partner identity, begin, local recovery | First person's selections leak through stale UI or browser history |
| S07 | Matching transition | Saving, matching, reduced motion, failure recovery | Fixed timers race backend completion |
| S08 | Viewer and profile selection | Couple, either solo profile, profile create/save/error, distinct identities | Actor-to-profile and solo-partner mapping changes |
| S09 | Tonight defaults and constraints | Language, availability, session mode, save, local fallback, error | Labels drift from backend provider and scoring mappings |
| S10 | Required onboarding | Loved, Ok, No buckets, partial completion, next person, unresolved title, failure | Shared mode unlocks before both profiles are complete |
| S11 | Tonight natural-language intent | Type, interpret, clarify once, editable signals, confirm, clear, offline/error | Stale or unconfirmed interpretation affects the session |
| S12 | Shortlist generation and recovery | Honest loading stages, live failure, local fallback, empty candidate recovery, retry | Flow advances with fewer than five usable candidates |
| S13 | Five-more and steer refinement | Same direction, quick steer, language steer, clarification, confirmed nudge, loading/error | Prior context or shown-title exclusion is lost |
| S14 | Shared watchlist | Loading, empty, save, saved plus undo, list, remove, watched, per-profile ratings, errors | One busy flag ambiguously disables every entry |
| S15 | Outcome and post-watch feedback | Watched winner, watched other, nothing, optional note, separate profile ratings, success/error | Duplicate submission and feedback without a watched title |
| S16 | Profile memory snapshot | Loading, learning, populated profiles, overlap, progressive detail, error | Weak evidence is presented as confident personal knowledge |
| S17 | Lightweight household history | Visible entry, loading, empty, session list, detail, back, error | Public history exposes internal score evidence or lacks dates |
| S18 | Taste Lab | Profile, queue loading, one active decision, batch progress, exhausted/offline/save states | Research and model language dominates the household task |
| S19 | Household login | Empty validation, show/hide passphrase, submitting, wrong phrase, success redirect | Redirect loop or weakened session handling |
| S20 | Separate setup utility | Profiles, defaults, ready, unsaved, saving, saved, disconnected | Duplicate controls drift from in-flow setup |
| S21 | Credits and asset provenance | TMDB attribution, back path, missing provider/image attribution | Cinematic shell hides legally required attribution |
| S22 | Debug and review quarantine | Review notes and raw evidence remain usable only through explicit review mode | Internal vocabulary leaks into the household flow |
| S23 | Cross-surface final gate | 320 to 430 widths, 390 by 844 flow, short height, keyboard, zoom, contrast, offline, reduced motion, build and tests | Individually polished surfaces fail as one complete journey |

## Canonical fixture

Unless a slice requires a specific failure or empty state, every production capture uses the same deterministic household fixture.

- The phone viewport is 390 by 844 CSS pixels with reduced motion off for the primary capture.
- The household is a couple with two distinct stable profile IDs labelled Husband and Wife.
- The language setting is English audio and subtitles are acceptable.
- The availability region is Germany and the provider constraint is Prime Video.
- The confirmed Tonight intent is `thoughtful and tense, without going bleak, under two hours`.
- The ranked set contains exactly Arrival, Knives Out, The Grand Budapest Hotel, Past Lives, and Edge of Tomorrow.
- Arrival is first with an 84 match score and a 12-point lead.
- The remaining visible scores are 72, 61, 52, and 38 in rank order.
- Both profiles mark Arrival Interested.
- The short reason is `Both wanted thoughtful sci-fi, and this stays tense without going bleak.`
- The movie imagery, synopsis, cast, and provider metadata use the golden manifest's verified TMDB assets or deterministic local fixture equivalents.
- Failure, empty, offline, slow-image, and long-copy captures derive from this fixture by changing only the state under test.

## Required evidence package

Every slice stores items one through seven before judgment begins.
The critic appends items eight and nine during judgment, and all nine items must exist before acceptance.

1. A named fixture and exact starting state.
2. A masked 390 by 844 candidate screenshot and the equivalent comparison screenshot.
3. The random seed and left-right assignment stored outside the critic's pre-verdict context.
4. A plain list of required interactions and their observed results.
5. A 320, 390, and 430 pixel overflow and reachability check.
6. Slice-appropriate keyboard, focus, Escape, 200 percent zoom, contrast, reduced-motion, missing-image, and offline checks.
7. Production build and relevant state-test output.
8. The critic's pre-unblinding scores, selected panel, and single biggest visible gap.
9. The critic's post-unblinding functional verdict and explicit accept or reject decision.

## Blind comparison procedure

1. Capture candidate and comparison with the same viewport, fixture, content, image state, and motion preference.
2. Remove filenames, route names, prototype labels, timestamps, and any other source-identifying metadata.
3. Assign neutral labels such as Panel X and Panel Y using a recorded random seed.
4. Randomize the left-right order and hide the source code, changelog, and builder notes from the critic until the visual verdict is written.
5. Score all categories and select X, Y, or tie for each category.
6. Record the single biggest visible gap before unblinding.
7. Unblind only after the visual verdict.
8. Inspect the real candidate and complete the functional, responsive, accessibility, motion, missing-data, and recovery checks.
9. Reject when the blind visual result or any hard functional gate fails.

## Judge scorecard

Every slice receives a blind or label-masked comparison where the visual artifact allows it.
The judge scores each category from zero to five and records the single biggest remaining gap.

| Category | Pass condition |
| --- | --- |
| Visual hierarchy and emotional quality | At least 4, with no current-production artifact judged preferable to the candidate |
| Golden-system fidelity | At least 4 for cinema surfaces and at least 3 for utility surfaces without inappropriate literal copying |
| Task clarity and word economy | At least 4, with one dominant action and no exposed internal vocabulary |
| Cross-surface product coherence | At least 4, with typography, controls, iconography, color, and state language recognizably belonging to one product |
| Functional fidelity | 5, with all locked invariants preserved |
| Mobile composition | At least 4 at 390 by 844 and no clipping at 320 pixels wide |
| Accessibility and resilience | At least 4 with no critical keyboard, focus, contrast, motion, or recovery failure |
| Overall finish | At least 4 and no unresolved gap classified as material |

A Cinema slice is accepted only at 35 out of 40 or higher, with functional fidelity at five, every other category at four or higher, and no material remaining gap.
A Utility slice is accepted only at 32 out of 40 or higher, with functional fidelity at five, every other category at four or higher, and no material remaining gap.
S01 remains provisionally held after its isolated primitive review and can be accepted only after its primitives pass on both S02 Cinema and a real Utility slice.

## Slice-specific hard rejects

- S01 rejects internal vocabulary, inconsistent shared controls, missing focus or reduced-motion behavior, global prototype regressions, or primitives that fail on either a Cinema or Utility harness.
- S02 rejects anything other than five total ranked titles, a missing meaningful gap, missing active-title switching, scores that imply identical confidence, or actions hidden below the primary viewport.
- S03 rejects missing synopsis, cast, reasons, or provider state, false launch behavior, or broken focus, Escape, backdrop-close, or focus return.
- S04 rejects a blank poster, duplicate or skipped vote, unexplained delay beyond 320 milliseconds after persistence completes, or Seen before substituting for tonight's reaction.
- S05 rejects wrong-profile memory, memory counting as a vote, or broken cancel, error, and return-to-reaction behavior.
- S06 rejects any first-ballot detail visible to the second person or recoverable through the household browser-back experience.
- S07 rejects artificial waiting, motion beyond 850 milliseconds after matching completes, lost state on failure, or absent reduced-motion behavior.
- S08 rejects changed couple or solo actor mapping, ambiguous identity, or discarded create and save input after an error.
- S09 rejects changed language, provider, or session-mode mapping, silent defaults, or implementation vocabulary.
- S10 rejects unlock without Loved, Ok, and No for each participating profile or any cross-profile seed write.
- S11 rejects unconfirmed intent affecting recommendations, language-model ranking ownership, more than one clarification, or lost input after error.
- S12 rejects advancement with fewer than five unique usable titles, repeated candidates on retry, or concealed fallback behavior.
- S13 rejects any repeated shown title, lost prior reaction or intent context, or application of an unconfirmed steer.
- S14 rejects wrong-entry or wrong-profile mutations, one busy state disabling unrelated entries, or missing undo and error recovery.
- S15 rejects duplicate submission, cross-profile ratings, feedback without a watched title, or a retry that loses the draft.
- S16 rejects weak evidence stated as certainty, swapped profiles, or absent loading, learning, and error states.
- S17 rejects raw diagnostic evidence, missing temporal recognition, or list-detail-back navigation that loses state.
- S18 rejects familiarity being treated as preference, lost batch choices, absent exhausted or offline behavior, or dashboard-like first-viewport density.
- S19 rejects passphrase disclosure, failed reveal and validation controls, redirect loops, or missing error focus.
- S20 rejects settings drift, silent loss of unsaved work, or any server address in household-facing hierarchy.
- S21 rejects missing TMDB attribution, confused asset ownership, or an unusable back path.
- S22 rejects review-mode reachability from ordinary household UI or any raw IDs, score internals, and implementation evidence outside explicit review mode.
- S23 rejects any supported-width, keyboard, zoom, contrast, offline, reduced-motion, build, state-test, or complete-journey failure.
