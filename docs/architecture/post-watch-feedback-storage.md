# Post-Watch Feedback Storage

Issue 10 stores post-watch feedback through a small service and SQLite store.
The API route layer is intentionally not wired in this slice.

```mermaid
flowchart LR
    A["Future API route"] --> B["PostWatchFeedbackService"]
    B --> C["SQLiteFeedbackStore"]
    C --> D[("post_watch_feedback")]
```

The service accepts a household id, session id, participant id, source movie id, feedback label, and optional note.
The stored feedback label is normalized to `loved`, `fine`, or `no`.
Blank household, session, participant, and title ids are rejected before a row is written.
Optional free-text notes are stored as raw text after trimming whitespace.

The table uses `(household_id, session_id, user_id, source_movie_id)` as its primary key.
Saving feedback for the same participant and title updates the existing record.
This keeps the MVP behavior forgiving when someone changes their mind after the first tap.

The domain model stays unchanged for now.
`PostWatchFeedback` remains the application-level feedback record.
The household id lives at the store boundary because listing feedback by household is a persistence concern.

Outcome capture and watched-history updates remain for the future API-facing Issue 10 slice.
This worker only implements the backend service and storage core requested for parallel development.
