# Current UX Map

All screenshots in this audit were captured at a narrow mobile viewport of `390x844`.

## Main User Flows

- `Pass-the-phone recommendation flow` starts on setup, moves through first-pass reactions, handoff, second-pass reactions, and ends on shared results.
- `Tonight intent flow` starts from setup, lets the user type a one-night preference steer, and feeds that into the recommendation setup before the first pass.
- `Taste memory flow` starts inside a reaction card when the user taps `Seen before`, then saves a memory note before the normal reaction continues.
- `Outcome and follow-up flow` starts from results, where the user can save to watchlist, record what was watched, and leave post-watch feedback when backend sync is active.
- `Recovery and inspection flow` starts from setup or results through history, review notes, and sync or error messaging.

## Global UI States

- `Loading` is represented by the cinematic launch sting and by smaller sync/loading labels during API-backed actions.
- `Ready` is represented by the setup screen, reaction cards, handoff screen, and results screen.
- `Expanded detail` is represented by the reaction card `More` state and the results explanation area.
- `Empty` is currently most explicit in the watchlist panel.
- `Error` is currently most explicit in the disconnected setup shell when FastAPI is unavailable.
- `Saved` is currently most explicit in the watchlist panel after a title has been added.

## Screen Inventory

### 1. Launch Sting

Screenshot: `screens/loading-launch-mobile.png` and `screens/00-launch.png`.

- `Screen name`: Launch sting.
- `What the user is trying to do`: Wait for the app shell to open and orient to the brand moment before setup appears.
- `Primary action`: None.
- `Secondary actions`: None.
- `Confusing elements`: It reads as a splash sequence rather than actionable loading, so it does not say what is being prepared or how long it will take.
- `Visual hierarchy notes`: The full-screen artwork and logo dominate completely, and there is no competing information.
- `Obvious missing states`: There is no explicit loading progress or fallback copy if startup stalls.

### 2. Landing / Start Screen

Screenshot: `screens/landing-start-mobile.png` and `screens/01-setup.png`.

- `Screen name`: Setup and start screen.
- `What the user is trying to do`: Confirm who is playing, the language and availability rules, and begin the recommendation flow.
- `Primary action`: `Start first pass`.
- `Secondary actions`: Change people mode, language mode, availability, session mode, and open supporting disclosures.
- `Confusing elements`: The screen presents several control groups at once, and the difference between session-level rules, profile setup, and one-night steering is not fully separated.
- `Visual hierarchy notes`: The hero art and title are strong, the primary button is clear, and the row summaries compress a lot of setup into a compact control-board metaphor.
- `Obvious missing states`: There is no explicit high-level summary of what will happen after tapping start beyond the smaller supporting copy.

### 3. Movie Preference Input State

Screenshot: `screens/preference-input-mobile.png`.

- `Screen name`: Tonight intent input.
- `What the user is trying to do`: Add a temporary preference steer for this specific movie night.
- `Primary action`: Type into the tonight-intent field and review the interpretation.
- `Secondary actions`: Leave the field empty and continue with the default setup, or clear a previously applied steer.
- `Confusing elements`: This area competes with the permanent setup controls on the same screen, so it is easy to read it as profile editing rather than a one-night override.
- `Visual hierarchy notes`: The input block is visible but secondary to the setup hero and start button, which keeps momentum but lowers discoverability.
- `Obvious missing states`: There is no prominent preview of how strongly the typed steer will change the shortlist before review.

### 4. Reaction Card With Details Expanded

Screenshot: `screens/reaction-details-mobile.png` and `screens/02-reaction-first.png`.

- `Screen name`: First-pass reaction card with expanded movie details.
- `What the user is trying to do`: Judge one candidate quickly and optionally inspect extra detail before reacting.
- `Primary action`: Choose `Interested`, `Maybe`, or `No`.
- `Secondary actions`: Open `More`, go back, or save a `Seen before` memory.
- `Confusing elements`: The card mixes recommendation reasons, synopsis-like detail, and language access in one expandable block, so the difference between explanation and metadata is blurry.
- `Visual hierarchy notes`: Poster, title, and reaction controls are strong, and the progress bar helps maintain pace through the five-card loop.
- `Obvious missing states`: There is no distinct skipped or undecided state beyond `Maybe`, and there is no explicit confidence explanation attached to the reaction itself.

### 5. Handoff Screen

Screenshot: `screens/handoff-mobile.png`.

- `Screen name`: Pass-the-phone handoff.
- `What the user is trying to do`: Hand the device to the second participant without leaking the first participant’s detailed picks.
- `Primary action`: `Start second pass`.
- `Secondary actions`: Go back.
- `Confusing elements`: The summary stats are clear, but the screen does not strongly explain whether the second person will see the same titles in the same order or how overlap is protected.
- `Visual hierarchy notes`: The handoff illustration and single next-step button make this one of the clearest transition screens in the app.
- `Obvious missing states`: There is no explicit privacy or reset cue if the second participant sees the prior screen before the handoff is tapped.

### 6. Recommendation Results

Screenshot: `screens/results-mobile.png`.

- `Screen name`: Shared recommendation results.
- `What the user is trying to do`: See the winning pick, understand the backups, and decide what to do next.
- `Primary action`: Continue with the winner or refine the next five.
- `Secondary actions`: Save to watchlist, start a new night, open outcome capture, inspect evidence, and review notes.
- `Confusing elements`: The page stacks winner reveal, backup picks, explanation, watchlist, outcome capture, debug evidence, and notes on one long surface, so the next best action is not always obvious.
- `Visual hierarchy notes`: The winning poster, score, and `Why this won` block land clearly above the fold and give the result a good reveal moment.
- `Obvious missing states`: There is no compact success state that cleanly separates `we have a pick` from the longer post-result workspace below it.

### 7. Movie Details / Explanation State

Screenshot: `screens/results-explanation-mobile.png`.

- `Screen name`: Results explanation and evidence view.
- `What the user is trying to do`: Understand why these five titles were chosen and why the top pick moved or held.
- `Primary action`: Read the evidence.
- `Secondary actions`: Continue downward into watchlist and outcome actions.
- `Confusing elements`: The explanation language mixes product-facing copy with scoring-facing language like signals, source, and held-back penalties, which may feel more diagnostic than consumer-friendly.
- `Visual hierarchy notes`: The grid breaks the explanation into understandable chunks, but it still reads denser than the rest of the flow and feels closer to a debug panel than a reveal panel.
- `Obvious missing states`: There is no lightweight explanation summary for users who want reassurance without reading a full evidence block.

### 8. Saved / Watchlist State

Screenshot: `screens/watchlist-saved-mobile.png`.

- `Screen name`: Shared watchlist with saved title.
- `What the user is trying to do`: Keep the current pick for later and optionally rate it per participant after it is watched.
- `Primary action`: Manage the saved watchlist item.
- `Secondary actions`: Mark watched, remove, or tap the `Loved`, `Fine`, and `No` chips per participant.
- `Confusing elements`: The watchlist, watched action, and per-person rating chips appear together, which makes it unclear whether this is pre-watch saving, post-watch logging, or both.
- `Visual hierarchy notes`: The saved card is readable and compact, but the rating grid becomes dense quickly for a phone-first flow.
- `Obvious missing states`: There is no clean confirmed `saved` success state separate from the management state once the card appears.

### 9. Empty State

Screenshot: `screens/watchlist-empty-mobile.png`.

- `Screen name`: Empty watchlist.
- `What the user is trying to do`: Understand where saved titles will appear if they use the watchlist.
- `Primary action`: None inside the panel itself.
- `Secondary actions`: Return to surrounding results actions and save a title.
- `Confusing elements`: The empty copy is clear, but the panel depends on the user already understanding the distinction between watchlist, outcome capture, and backup picks.
- `Visual hierarchy notes`: The empty state is understated and easy to miss because it sits below several heavier results sections.
- `Obvious missing states`: There is no stronger empty-state affordance that pulls the user back to the exact save action above.

### 10. Error State

Screenshot: `screens/error-disconnected-mobile.png`.

- `Screen name`: Disconnected setup shell.
- `What the user is trying to do`: Understand whether the app can reach FastAPI and whether setup is safe to continue.
- `Primary action`: Continue in the local shell if desired.
- `Secondary actions`: Adjust setup controls and retry later by refreshing.
- `Confusing elements`: The screen still looks mostly ready to start, so the practical consequence of being disconnected is not explained strongly enough in the main action area.
- `Visual hierarchy notes`: The disconnected pill is visible, but it is small compared with the cinematic hero and the large start button.
- `Obvious missing states`: There is no prominent recovery action or plain-English explanation of which capabilities degrade when the backend is unavailable.

## Observed Gaps

- The app has a strong phone-first visual direction, but the setup and results screens each carry many responsibilities on one surface.
- The current UX relies heavily on long-scroll comprehension after the result reveal.
- Save, watched, and post-watch feedback states exist, but they are not cleanly separated into pre-watch and post-watch modes.
- Some useful states are implemented but not surfaced as distinct moments, especially loading, save confirmation, and backend degradation.
- I did not find a distinct standalone `dismissed` state outside normal reaction choices and post-watch rating controls.
