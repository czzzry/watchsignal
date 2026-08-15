"use client";

import type { FeedbackNoteState, FeedbackState, RankedCandidate } from "../../pass-the-phone-model";
import type { SessionOutcomePayload, SessionOutcomeType } from "../../session-client";
import { WatchSignalIcon } from "../../ui/watchsignal-icons";
import type { ResultsParticipantEntry } from "./results-panels";
import styles from "./outcome-utility.module.css";

const ratingChoices = [["loved", "Loved"], ["fine", "Fine"], ["no", "No"]] as const;

export function OutcomeUtility({ rankedCandidates, participants, outcomeType, otherPickId, note, savedOutcome, watchedTitle, outcomeError, feedbackError, feedbackState, feedbackNotes, outcomeBusy, outcomeConfirmed, feedbackBusy, canPersist, canSaveOutcome, feedbackReady, savedFeedbackProfileIds, onBack, onOutcomeType, onOtherPick, onNote, onSaveOutcome, onFeedback, onFeedbackNote, onSaveFeedback, onPosterFallback }: {
  rankedCandidates: RankedCandidate[];
  participants: ResultsParticipantEntry[];
  outcomeType: SessionOutcomeType | null;
  otherPickId: string | null;
  note: string;
  savedOutcome: SessionOutcomePayload | null;
  watchedTitle: RankedCandidate | null;
  outcomeError: string | null;
  feedbackError: string | null;
  feedbackState: FeedbackState;
  feedbackNotes: FeedbackNoteState;
  outcomeBusy: boolean;
  outcomeConfirmed: boolean;
  feedbackBusy: boolean;
  canPersist: boolean;
  canSaveOutcome: boolean;
  feedbackReady: boolean;
  savedFeedbackProfileIds: string[];
  onBack: () => void;
  onOutcomeType: (value: SessionOutcomeType) => void;
  onOtherPick: (movieId: string) => void;
  onNote: (note: string) => void;
  onSaveOutcome: () => void | Promise<void>;
  onFeedback: (profileId: string, value: "loved" | "fine" | "no") => void;
  onFeedbackNote: (profileId: string, note: string) => void;
  onSaveFeedback: () => void | Promise<void>;
  onPosterFallback: (event: { currentTarget: HTMLImageElement }) => void;
}) {
  const winner = rankedCandidates[0];
  const feedbackVisible = savedOutcome && savedOutcome.outcomeType !== "watched_nothing" && watchedTitle;
  return (
    <section className={styles.page} aria-labelledby="outcome-title">
      <header className={styles.header}>
        <button type="button" onClick={onBack} aria-label="Back to result options"><WatchSignalIcon name="arrow-left" /></button>
        <div><span>After tonight</span><h2 id="outcome-title">What happened?</h2></div>
      </header>

      {!feedbackVisible ? (
        <>
          <div className={styles.choices} role="group" aria-label="What happened tonight">
            <button type="button" aria-pressed={outcomeType === "watched_recommended"} onClick={() => onOutcomeType("watched_recommended")}><WatchSignalIcon name="play" /><span><strong>Watched {winner?.title ?? "the winner"}</strong><small>Tonight’s first pick</small></span></button>
            <button type="button" aria-pressed={outcomeType === "watched_other"} onClick={() => onOutcomeType("watched_other")}><WatchSignalIcon name="film" /><span><strong>Watched another</strong><small>Choose from the shortlist</small></span></button>
            <button type="button" aria-pressed={outcomeType === "watched_nothing"} onClick={() => onOutcomeType("watched_nothing")}><WatchSignalIcon name="close" /><span><strong>Nothing tonight</strong><small>Keep the result, skip ratings</small></span></button>
          </div>

          {outcomeType === "watched_other" ? <div className={styles.movies} role="group" aria-label="Movie watched">{rankedCandidates.slice(1).map((movie) => <button key={movie.id} type="button" aria-pressed={otherPickId === movie.id} onClick={() => onOtherPick(movie.id)}><img src={movie.posterUrl} alt="" onError={onPosterFallback} /><span>{movie.title}</span></button>)}</div> : null}

          <label className={styles.note}><span>Note <small>Optional</small></span><textarea value={note} onChange={(event) => onNote(event.target.value)} rows={3} placeholder="Anything worth remembering?" /></label>
          {!canPersist ? <p className={styles.error} role="status">Saving after tonight needs a connected session.</p> : null}
          {outcomeError ? <p className={styles.error} role="alert">{outcomeError}</p> : null}
          <button className={styles.primary} type="button" aria-live="polite" disabled={!canSaveOutcome || outcomeBusy} onClick={() => void onSaveOutcome()}>{outcomeBusy ? "Saving…" : outcomeConfirmed ? "Saved" : outcomeError ? "Retry" : outcomeType === "watched_nothing" ? "Save and finish" : "Save and rate"}</button>
        </>
      ) : (
        <>
          <div className={styles.watched}><span><WatchSignalIcon name="check" /></span><div><small>Watched</small><strong>{watchedTitle.title}</strong></div></div>
          <div className={styles.feedback}>
            {participants.map((person) => <section key={person.id}><h3>{person.label}{savedFeedbackProfileIds.includes(person.id) ? <small>Saved</small> : null}</h3><div role="group" aria-label={`${person.label} post-watch rating`}>{ratingChoices.map(([value,label]) => <button type="button" key={value} aria-pressed={feedbackState[person.id] === value} onClick={() => onFeedback(person.id,value)} disabled={feedbackBusy}>{label}</button>)}</div><label><span>Note <small>Optional</small></span><textarea rows={2} value={feedbackNotes[person.id] ?? ""} onChange={(event) => onFeedbackNote(person.id,event.target.value)} placeholder="What should we remember?" disabled={feedbackBusy} /></label></section>)}
          </div>
          {feedbackError ? <p className={styles.error} role="alert">{feedbackError}</p> : null}
          <button className={styles.primary} type="button" disabled={!feedbackReady || feedbackBusy} onClick={() => void onSaveFeedback()}>{feedbackBusy ? "Saving…" : feedbackError ? "Retry ratings" : savedFeedbackProfileIds.length === participants.length ? "Ratings saved" : savedFeedbackProfileIds.length > 0 ? "Save changes" : "Save ratings"}</button>
        </>
      )}
    </section>
  );
}
