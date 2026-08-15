"use client";

import { useState } from "react";
import type { WatchlistEntryPayload } from "../../session-client";
import { WatchSignalIcon } from "../../ui/watchsignal-icons";
import type { ResultsParticipantEntry } from "./results-panels";
import {
  watchlistEntryAction,
  type WatchlistEntryBusyState,
} from "./watchlist-contract";
import styles from "./watchlist-utility.module.css";

const ratings = [
  ["loved", "Loved"],
  ["fine", "Fine"],
  ["no", "No"],
] as const;

export function WatchlistUtility({
  entries,
  participants,
  loading,
  available,
  message,
  ratingState,
  entryBusy,
  watchedState,
  onBack,
  onRetry,
  onRating,
  onWatched,
  onRemove,
}: {
  entries: WatchlistEntryPayload[];
  participants: ResultsParticipantEntry[];
  loading: boolean;
  available: boolean;
  message: string | null;
  ratingState: Record<string, Record<string, "loved" | "fine" | "no">>;
  entryBusy: WatchlistEntryBusyState;
  watchedState: Record<string, true | undefined>;
  onBack: () => void;
  onRetry: () => void | Promise<void>;
  onRating: (movieId: string, profileId: string, rating: "loved" | "fine" | "no") => void;
  onWatched: (entry: WatchlistEntryPayload) => void | Promise<void>;
  onRemove: (movieId: string) => void | Promise<void>;
}) {
  return (
    <section className={styles.page} aria-labelledby="shared-watchlist-title">
      <header className={styles.header}>
        <button type="button" onClick={onBack} aria-label="Back to result options"><WatchSignalIcon name="arrow-left" /></button>
        <div><span>Shared</span><h2 id="shared-watchlist-title">Watchlist</h2></div>
        <strong>{entries.length}</strong>
      </header>

      {!available ? (
        <div className={styles.empty}>
          <span aria-hidden="true"><WatchSignalIcon name="bookmark" /></span>
          <h3>Watchlist unavailable</h3>
          <p>Reconnect to view or change the shared watchlist.</p>
        </div>
      ) : loading ? (
        <div className={styles.loading} role="status"><i /><i /><i /><span>Loading saved movies…</span></div>
      ) : entries.length === 0 ? (
        <div className={styles.empty}>
          <span aria-hidden="true"><WatchSignalIcon name="bookmark" /></span>
          <h3>Nothing saved yet</h3>
          <p>Save a result and it will wait here for both of you.</p>
          {message ? <button type="button" onClick={() => void onRetry()}>Try again</button> : null}
        </div>
      ) : (
        <div className={styles.list}>
          {entries.map((entry) => (
            <WatchlistRow
              key={entry.sourceMovieId}
              entry={entry}
              participants={participants}
              ratings={ratingState[entry.sourceMovieId] ?? {}}
              busy={watchlistEntryAction(entryBusy, entry.sourceMovieId)}
              watched={Boolean(watchedState[entry.sourceMovieId])}
              onRating={onRating}
              onWatched={onWatched}
              onRemove={onRemove}
            />
          ))}
        </div>
      )}
      {message ? <p className={styles.message} role={/couldn|need/i.test(message) ? "alert" : "status"}>{message}</p> : null}
    </section>
  );
}

function WatchlistRow({ entry, participants, ratings: selectedRatings, busy, watched, onRating, onWatched, onRemove }: {
  entry: WatchlistEntryPayload;
  participants: ResultsParticipantEntry[];
  ratings: Record<string, "loved" | "fine" | "no">;
  busy: "removing" | "marking" | null;
  watched: boolean;
  onRating: (movieId: string, profileId: string, rating: "loved" | "fine" | "no") => void;
  onWatched: (entry: WatchlistEntryPayload) => void | Promise<void>;
  onRemove: (movieId: string) => void | Promise<void>;
}) {
  const [posterFailed, setPosterFailed] = useState(false);
  return (
    <article className={styles.row} aria-label={entry.title}>
      <div className={styles.movie}>
        {entry.posterUrl && !posterFailed ? <img src={entry.posterUrl} alt="" onError={() => setPosterFailed(true)} /> : <i aria-label={`${entry.title} poster unavailable`}>W</i>}
        <div><strong>{entry.title}</strong><span>{entry.releaseYear ?? "Saved movie"}</span></div>
        <button type="button" onClick={() => void onRemove(entry.sourceMovieId)} disabled={busy !== null} aria-label={`Remove ${entry.title}`}><WatchSignalIcon name="close" /></button>
      </div>
      <div className={styles.ratings}>
        {participants.map((person) => (
          <div key={person.id}>
            <span>{person.label}</span>
            <div role="group" aria-label={`${person.label} rating for ${entry.title}`}>
              {ratings.map(([value, label]) => <button key={value} type="button" aria-pressed={selectedRatings[person.id] === value} onClick={() => onRating(entry.sourceMovieId, person.id, value)} disabled={busy !== null}>{label}</button>)}
            </div>
          </div>
        ))}
      </div>
      <button className={styles.watched} type="button" onClick={() => void onWatched(entry)} disabled={busy !== null || watched}>{busy === "marking" ? "Saving…" : watched ? "Watched saved" : "Mark watched"}</button>
    </article>
  );
}
