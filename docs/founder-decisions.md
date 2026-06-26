# Founder Decisions

This document captures the founder decisions made during the grill session.
It is the short-form companion to [decision-register.md](/Users/cezarybaraniecki/Documents/n8n%20movie%20recommender/docs/decision-register.md).
These decisions guide the first vertical slice.
They do not replace ADRs for later architecture changes.

## Product direction

- This project is a private household mediator, not a public movie product
- The job is to help two people watch more movies and shows they actually enjoy
- The system should learn each person's taste separately and improve shared outcomes over time
- The end state should pursue real recommendation sophistication, even if MVP starts simpler

## Locked decisions

- Interface: Telegram first
- Shared input modes: separate-device is primary and pass-the-phone must also work
- Metadata source: TMDb first
- Availability requirement: Amazon.de must be modeled as a normal session constraint
- Language requirement: default to English audio or foreign-language with English subtitles, with rare override cases allowed
- Storage: Google Sheets first
- Orchestration boundary: n8n orchestrates, but scoring lives behind a separate testable module
- Deployment posture: start on n8n Cloud if convenient, but stay portable to self-hosted n8n
- Repo posture: private working repo first, sanitized public artifacts later only if worthwhile

## Recommendation posture

- Version one favors fast learning and reliability over full sophistication
- Version one must still preserve a clean upgrade path to a stronger recommender
- Recommendation quality matters more than perfect explainability
- Explanations are still part of the product because they help build trust
- The shortlist should visibly distinguish current mode, personal fit, and compromise fit
- The mature recommendation engine is expected to be hybrid rather than purely heuristic or purely LLM-driven
- Structured scoring remains valuable even if later LLM enrichment becomes important
- Free-text notes are expected to become more valuable once LLM interpretation is added

## Session behavior

- Default content type is movie unless switched to TV
- The first question in a shared session is who is watching
- If both are watching, the app should show the current default mode and allow override
- If the user selects husband, wife, or both from a recommendation entry prompt, downstream flows should preserve that choice instead of asking for the same identity again when onboarding is triggered
- Session mode can be husband-first, wife-first, or compromise
- Single-viewer sessions should ignore the absent person's taste completely
- Shared sessions should allow asynchronous scoring
- Timed-out shared sessions should pause and resume later

## Feedback model

- Onboarding is required before the first real recommendation
- One-sided onboarding is enough for one-person sessions
- Both users must onboard before compromise or shared recommendation mode is unlocked
- Onboarding should lean heavily on manual seed titles
- A short preference interview is still useful for strong constraints
- Shortlist feedback uses Interested or Maybe or No
- Post-watch feedback uses Loved or Fine or No
- Where practical, Telegram feedback prompts should also accept numeric aliases for the same choices to reduce typing friction
- Optional free-text feedback is captured from day one
- Optional free-text feedback is stored immediately for later interpretation, even if MVP uses it mainly for debugging and manual review at first
- Already-seen backfill and manual watched-history backfill are part of MVP

## Defaults and constraints

- Remember common defaults between sessions
- Keep defaults visible and easy to override
- Treat Prime Germany as a common remembered default, not a hard-coded forever rule
- Treat language preference as an effectively hard default for normal use
- Do not treat runtime as a remembered default at first
- Treat rewatch avoidance as a household default
- Start MVP hard constraints with runtime, service availability, rewatch avoidance, horror exclusion, and subtitle intolerance where relevant

## Trust and measurement

- MVP success is real household behavior, not just technical completion
- Bad recommendations are acceptable at first if there is a clear recorded trend of improvement
- Track product metrics from the start
- Keep a visible lightweight history for users
- Keep deeper session artifacts internally for debugging and later analysis
- Make uncertainty visible and friendly rather than pretending confidence

## First vertical slice

- Required onboarding
- Telegram session start
- Shared or solo mode selection
- Shortlist generation
- Per-person shortlist reactions
- Strong recommended pick plus visible reranked shortlist
- Outcome capture
- Post-watch feedback
- Storage of session artifacts and feedback in visible operating storage

## MVP plus 1

- LLM-assisted interpretation of free-text feedback and human reasons for rejecting titles
- Stronger recommendation learning from session outcomes
- Continued portability discipline
- Diagram updates that reflect the real system rather than the intended system
- Better feedback-context UX so the bot reminds the user which prior recommendation session they are resolving when memory may be fuzzy
- A pre-recommend reminder that offers a tappable feedback continuation when the prior recommendation session still lacks outcome or post-watch feedback
- LLM-assisted enrichment of recommendation reasoning without making the LLM the only ranking authority
- Improved shortlist blurbs so raw TMDb summaries are not truncated awkwardly in Telegram
- A better calibration response for "seen long ago / unsure" so weak-memory titles are not forced into false positive or false negative taste signal

## MVP plus N

- onboarding UX simplification and guided seeding review after the first live learning loop is proven
- On-demand taste profile snapshots
- "Ideal movie" synthesis per person
- Existing-show episode recommender for known series
- Deeper review surfaces for history and analysis
- Richer LLM-generated taste interpretation in the mature product
