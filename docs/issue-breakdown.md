# MVP Issue Breakdown

This document refines the MVP PRD into vertical implementation slices.
It is the local draft that should later become GitHub Issues.
Each slice is meant to be independently understandable, demoable, and testable.

## Coverage note

This breakdown is intended to cover the MVP-scoped user stories from [prd-mvp.md](prd-mvp.md).
It does not fully implement the later ideas already parked in MVP plus 1 or MVP plus N.

## Slice 1 - Platform smoke test

- Type: AFK
- Blocked by: None
- Main purpose: prove the end-to-end toolchain before recommendation logic starts

### Artifacts or behavior added

- Minimal Telegram to n8n trigger proof
- Minimal n8n to Google Sheets write proof
- Minimal Telegram confirmation reply
- Small repo note about the verified platform path

### Acceptance criteria

- [ ] A Telegram command can trigger an n8n workflow successfully
- [ ] The workflow can write a visible row to the MVP Google Sheet
- [ ] The workflow can send a confirmation message back to Telegram
- [ ] The path is documented briefly enough that later slices can rely on it without repeating setup discovery

### Demo after this slice

- A user can send one Telegram command and see proof that Telegram, n8n, and Google Sheets are wired together correctly

### Founder-side setup likely needed

- Telegram bot creation
- n8n Cloud access
- Google Sheet creation

## Slice 2 - Set up MVP operating model and storage contracts

- Type: AFK
- Blocked by: None
- Main purpose: establish the durable seams and operating data model before workflow implementation starts

### Artifacts or behavior added

- Initial Google Sheets tab plan
- Session artifact shape
- Watched-history shape
- Metrics shape
- Scoring-module interface contract
- MVP architecture notes that tie repo artifacts to implementation seams

### Acceptance criteria

- [ ] The MVP operating entities are named and documented clearly enough to implement against
- [ ] The first Google Sheets tab set is defined for sessions, users, watched history, shortlist reactions, post-watch feedback, and metrics
- [ ] The scoring module has an explicit request and response contract
- [ ] The boundary between n8n orchestration and scoring logic is documented clearly enough to test independently

### Demo after this slice

- A reviewer can inspect the project docs and understand what state exists, what gets persisted, and where recommendation logic begins and ends

### Founder-side setup likely needed

- None required yet
- Optional: confirm naming preferences if any sheet or field names feel off later

## Slice 3 - Build solo onboarding and seed capture flow

- Type: AFK
- Blocked by: Slice 2
- Main purpose: let one user teach the system enough to unlock solo recommendations

### Artifacts or behavior added

- Solo onboarding flow shape
- Manual seed-title capture behavior
- Strong-constraint capture behavior
- Prompted seeding support design
- Google Sheets persistence for onboarding outputs

### Acceptance criteria

- [ ] One user can complete onboarding without the other user
- [ ] Seed titles can be recorded with the expected rating buckets
- [ ] Strong constraints such as language and horror tolerance can be persisted
- [ ] Onboarding outputs are written to visible operating storage

### Demo after this slice

- One user can complete a first-time setup path and inspect the stored onboarding result

### Founder-side setup likely needed

- Access to the already-verified Telegram, n8n Cloud, and Google Sheets setup

## Slice 4 - Build solo movie recommendation tracer bullet

- Type: AFK
- Blocked by: Slices 2 and 3
- Main purpose: make one complete end-to-end solo recommendation path real

### Artifacts or behavior added

- Telegram-triggered solo session start
- Default movie-first flow
- Minimal clarifying-question behavior
- TMDb candidate fetch integration
- Scoring-module call from n8n
- Shortlist delivery with posters and explanation blurbs

### Acceptance criteria

- [ ] A solo user can start a recommendation session in Telegram
- [ ] The system assumes movie mode by default unless changed
- [ ] The system asks only minimum required clarification questions
- [ ] Candidates are fetched from TMDb and passed through the scoring module
- [ ] A shortlist is returned with posters and short explanation blurbs

### Demo after this slice

- A solo user can start from Telegram and receive a shortlist that looks like a real product rather than a stub

### Founder-side setup likely needed

- TMDb API key
- Telegram and Google Sheets setup already in place

## Slice 5 - Add solo outcome capture, post-watch feedback, and metrics

- Type: AFK
- Blocked by: Slice 4
- Main purpose: close the solo learning loop so the system improves over time

### Artifacts or behavior added

- Outcome reconciliation flow
- Loved or Fine or No capture
- Optional free-text capture
- Early product metrics tracking

### Acceptance criteria

- [ ] The next interaction can ask what was actually watched
- [ ] The user can record watched recommended, watched something else, or watched nothing
- [ ] Post-watch feedback is stored using Loved or Fine or No
- [ ] Product metrics such as shortlist usage and restart patterns are persisted

### Demo after this slice

- A solo user can complete a recommendation loop and leave behind usable learning data

### Founder-side setup likely needed

- None beyond working Telegram, TMDb, and Google Sheets setup

## Slice 6 - Build shared-session intake and mode selection

- Type: AFK
- Blocked by: Slices 2 and 3
- Main purpose: let the product operate as a real two-person mediator

### Artifacts or behavior added

- Shared-session intake
- Visible shared-mode default and override
- Separate-device primary path
- Pass-the-phone supported path

### Acceptance criteria

- [ ] The system can distinguish solo and shared sessions
- [ ] Shared sessions support husband-first, wife-first, and compromise modes
- [ ] The current default mode is shown explicitly and can be overridden quickly
- [ ] The flow supports both separate-device and pass-the-phone participation

### Demo after this slice

- Two people can start a shared session with the correct mode and audience setup

### Founder-side setup likely needed

- Telegram access for both users if separate-device mode is being tested

## Slice 7 - Build shared shortlist reactions and reranked recommendation

- Type: AFK
- Blocked by: Slices 4 and 6
- Main purpose: collect both users' pre-watch intent and turn it into a shared recommendation outcome

### Artifacts or behavior added

- Interested or Maybe or No reaction flow
- Skip support
- Reranked shortlist output
- Strong recommendation and pick-for-us behavior

### Acceptance criteria

- [ ] Both users can react independently to shortlisted titles
- [ ] Users can skip items without the system treating the skip as neutral
- [ ] The system reranks the shortlist using both users' reactions and the active session mode
- [ ] The output includes a visible reranked shortlist, a strong recommendation, and a pick-for-us action

### Demo after this slice

- A shared session can turn two sets of shortlist reactions into a believable shared recommendation result

### Founder-side setup likely needed

- None beyond the prior Telegram access assumptions

## Slice 8 - Add shared async completion, timeout, and pause-resume

- Type: AFK
- Blocked by: Slice 7
- Main purpose: make shared sessions practical under real-life household timing

### Artifacts or behavior added

- Asynchronous completion support
- Timeout behavior
- Pause and resume behavior

### Acceptance criteria

- [ ] One user can finish scoring before the other
- [ ] Shared sessions do not require synchronized participation
- [ ] An unfinished shared session times out into pause-and-resume rather than a hidden fallback
- [ ] Resume state is persisted clearly enough to continue later

### Demo after this slice

- A shared session can be interrupted and later resumed without losing the recommendation context

### Founder-side setup likely needed

- None

## Slice 9 - Add already-seen correction and manual watched-history backfill

- Type: AFK
- Blocked by: Slice 5
- Main purpose: improve watched-state quality and taste-learning speed

### Artifacts or behavior added

- Already-seen correction path inside sessions
- Manual watched-history backfill flow
- We-both-watched-this shortcut with separate per-person reactions

### Acceptance criteria

- [ ] A shortlist item can be marked as already seen
- [ ] Already-seen correction can also capture Loved or Fine or No
- [ ] Users can manually backfill watched titles outside a live session
- [ ] A shared backfill path exists without collapsing separate personal reactions

### Demo after this slice

- The system can turn messy real-world history gaps into useful learning data

### Founder-side setup likely needed

- None

## Slice 10 - Add lightweight history and uncertainty UX

- Type: AFK
- Blocked by: Slices 5 and 7
- Main purpose: improve trust, inspectability, and recovery behavior

### Artifacts or behavior added

- Lightweight recent-history access
- Visible uncertainty explanations
- Correct branching when the system needs more seed data or more session-specific signal

### Acceptance criteria

- [ ] Users can review lightweight recent session history
- [ ] The system can explicitly admit uncertainty in a user-friendly way
- [ ] The uncertainty path distinguishes long-term taste gaps from session-context gaps
- [ ] Follow-up prompts align with the type of uncertainty detected

### Demo after this slice

- The product can explain when it is uncertain and show enough history to prove it is learning

### Founder-side setup likely needed

- None

## Slice 11 - Document MVP plus 1 upgrade lane and evaluation hooks

- Type: HITL
- Blocked by: Slices 5 and 7
- Main purpose: protect the long-term sophistication goal from being forgotten once MVP works

### Artifacts or behavior added

- Explicit MVP plus 1 recommendation-upgrade plan
- Evaluation hooks for future scoring improvements
- LLM-assisted feedback interpretation lane
- Diagram updates that reflect the real system shape after MVP

### Acceptance criteria

- [ ] The upgrade lane from MVP to MVP plus 1 is explicit and reviewable
- [ ] The scoring-evaluation hooks needed for later comparison work are identified
- [ ] LLM-assisted feedback interpretation is captured as the first sophistication upgrade
- [ ] Diagrams and architecture notes reflect the actual built MVP, not only the intended one

### Demo after this slice

- The founder can point to a concrete next-phase plan rather than a vague promise of future sophistication

### Founder-side setup likely needed

- Founder review and approval of the sophistication direction before implementation proceeds further

## Product evolution summary

### Slices 1 to 2

- Prove the platform path
- Define the operating shape
- Establish the first usable data model

### Slices 3 to 5

- Build onboarding
- Deliver a real solo recommendation loop
- Add the first measurable learning loop

### Slices 6 to 8

- Deliver real shared-session household behavior
- Make two-person usage practical in normal life

### Slices 9 to 10

- Improve history quality
- Improve trust, inspectability, and recovery behavior

### Slice 11

- Lock in the path to stronger recommendation sophistication after MVP
