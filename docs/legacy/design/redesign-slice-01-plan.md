# Redesign Slice 01 Plan

## Purpose

This plan defines the first real redesign implementation slice for Movie Night Mediator after the high-fidelity concept review.
It is intentionally narrow.
The goal is to prove the new visual direction in the real app without trying to redesign every screen at once.

## Slice objective

Ship the first user-visible product leap from prototype-feeling UI to flagship-feeling UI.

This slice should prove four things.

1. The app can have an ownable launch moment.
2. The startup screen can feel premium and current without losing clarity.
3. The reaction card can feel cinematic and helpful at the same time.
4. The `Also seen this` interaction can be clearly separated from tonight-fit reactions.

## In scope

This slice should include:

- launch/loading sting,
- startup screen redesign,
- reaction card redesign,
- progress/status redesign for these screens,
- separated memory action for `Also seen this`,
- richer reaction-card content surface,
- and visual-system translation into the real product shell.

## Out of scope

This slice should not include:

- full onboarding redesign implementation,
- results reveal redesign,
- recent nights redesign,
- founder review or debug surface redesign,
- post-watch feedback redesign,
- recommendation engine changes,
- or LLM recommendation explanation implementation.

Those can follow once the startup and reaction loop prove the visual system.

## User-facing outcomes

After this slice, a user should feel:

- the app has a real identity from the first second,
- the startup screen tells them exactly what to do next,
- the movie card feels like a real entertainment product experience,
- and the `Also seen this` action makes intuitive sense without confusing the main vote.

## Screen-by-screen plan

### Screen 1 - Launch/loading sting

#### Goal

Give the app an ownable branded opening moment that lasts briefly and feels premium.

#### Required behavior

- Show a short loading or opening overlay on app open.
- Use the TV-static motif or a close descendant.
- Keep the animation brief and non-annoying.
- Resolve into the correct next state once session and setup state are known.

#### Required design qualities

- Strong mood.
- Distinctive branding.
- Cleaner composition than the current app.
- Personality without feeling cheap or juvenile.

#### Open decision inside this slice

- Exact launch copy tone.

### Screen 2 - Startup screen

#### Goal

Make the home/start screen feel like a flagship consumer app while keeping the next action crystal clear.

#### Required behavior

- Support state-aware startup.
- Distinguish between setup-needed and ready-for-tonight states.
- Keep the main action obvious.
- Remove backend and debug language from the normal path.

#### Required design qualities

- Date-led confidence.
- Clean hierarchy.
- Premium cinematic shell.
- Minimal visual clutter.
- Strong main call to action.

#### Product controls to preserve

- `People` must remain adjustable.
- Support:
  - `Husband`
  - `Wife`
  - `Husband + Wife`
- `Language` must remain adjustable.
- Support:
  - `English`
  - `Foreign audio + English subtitles`
  - `No rules`

#### Likely implementation shape

- Main hero area.
- Cleaner progress treatment.
- Compact editable setup summary.
- Utility access to secondary controls instead of front-stage clutter.

### Screen 3 - Reaction card

#### Goal

Create a movie-by-movie decision screen that feels cinematic, premium, and genuinely helpful.

#### Required behavior

- One movie at a time.
- Main reactions:
  - `Interested`
  - `Maybe`
  - `No`
- Separate memory action:
  - `Also seen this`
- Memory action must not appear mutually exclusive with the main reactions.
- Preserve the ability to mark a movie as seen and still rate it for tonight.

#### Required design qualities

- Poster-led composition.
- Strong title and metadata hierarchy.
- Better supporting explanation.
- High scanability.
- More premium control feel.

#### Content requirements

- Add one fast confidence cue such as Rotten Tomatoes-style score or equivalent.
- Keep cast or supporting metadata visible only if it helps scanning.
- Preserve room for richer future explanation text.
- Keep a `More details` or equivalent expansion path for fuller context.

#### Interaction structure requirement

The screen should visually distinguish:
- `Tonight's fit` actions
- from `Past viewing / memory` actions

This is a core product clarity requirement, not a cosmetic preference.

### Progress/status treatment

#### Goal

Replace the current chunkier multi-pill process feel with something cleaner and more premium.

#### Required behavior

- Keep orientation clear.
- Indicate current position in the flow.
- Work across startup and reaction screens.

#### Current recommendation

- Single progress bar plus current-step label.

## Visual-system translation tasks

This slice is not only about screen layout.
It also needs the first concrete translation of the visual world into reusable app rules.

### Required translation areas

1. App shell spacing and depth.
2. Primary and secondary button language.
3. Progress bar component.
4. Poster framing treatment.
5. Card surface treatment.
6. Accent and glow rules.
7. Typography scale and weight rules.

## Delivery checklist

The slice should not be considered done unless all of these are true.

- The startup screen clearly reflects the locked visual direction.
- The reaction card clearly reflects the locked visual direction.
- `Also seen this` is visibly separated from the main reactions.
- The app feels meaningfully more premium on a phone-sized viewport.
- The new progress treatment is implemented and readable.
- The launch/loading moment is short and branded.
- The main path does not expose backend or debug language.
- The screens have been click-tested in a phone-sized browser viewport.

## Validation plan

### Visual validation

- Compare implemented startup and reaction screens against the locked concept direction.
- Check whether the app still feels cinematic and premium after real content is introduced.
- Confirm that the design did not collapse back into generic glass cards.

### UX validation

- Click through startup into first reaction.
- Confirm the user can tell what the main action is immediately.
- Confirm the user understands `Also seen this` is additive.
- Confirm the main reactions are still the obvious path.

### Technical validation

- Production build passes.
- Mobile viewport smoke pass succeeds.
- No obvious text overflow, clipping, or overlap.

## Main risks

### Risk 1 - Implementation drift

The UI could become a watered-down version of the concept if the team reverts to the old panel and button patterns.

Mitigation.
Use the locked visual direction summary as the implementation guardrail.

### Risk 2 - Beauty hurts clarity

The startup or reaction card could become more dramatic but less usable.

Mitigation.
Prioritize hierarchy and scanability over decorative intensity.

### Risk 3 - Signature moment becomes annoying

The loading sting could feel slow or gimmicky if it overstays its welcome.

Mitigation.
Keep it short and test it in repeated use.

## Recommended sequence inside the slice

1. Rebuild or restyle the app shell and progress treatment.
2. Implement the launch/loading sting.
3. Redesign the startup screen.
4. Redesign the reaction card.
5. Separate `Also seen this` into its own utility action area.
6. Run phone-sized click-through validation.

## Plain-English summary

The first redesign slice should prove the new north-star direction where it matters most: the moment the app opens and the moment the user starts judging movies.
If this slice works, the rest of the redesign will have a believable foundation.
If it does not work, we should fix it here before redesigning the rest of the product.
