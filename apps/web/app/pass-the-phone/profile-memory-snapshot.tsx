"use client";

import type { RefObject } from "react";
import type {
  ProfileMemorySummaryPayload,
  TasteMemoryEventPayload,
} from "../session-client";
import { AccessibleModal } from "../ui/accessible-modal";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import {
  buildProfileMemorySnapshot,
  householdMemorySummary,
  profileMemoryPublicMessage,
} from "./profile-memory-snapshot-contract";
import styles from "./profile-memory-snapshot.module.css";

export function ProfileMemorySnapshot({
  backgroundRef,
  opener,
  profileLabels,
  summaries,
  events,
  status,
  message,
  onRetry,
  onClose,
}: {
  backgroundRef: RefObject<HTMLElement | null>;
  opener: HTMLElement | null;
  profileLabels: Record<string, string>;
  summaries: ProfileMemorySummaryPayload[];
  events: TasteMemoryEventPayload[];
  status: "loading" | "ready" | "failed";
  message: string | null;
  onRetry: () => void | Promise<void>;
  onClose: () => void;
}) {
  const snapshots = summaries.map((summary) =>
    buildProfileMemorySnapshot(
      summary,
      events,
      profileLabels[summary.profileId] ?? "Household profile",
    ),
  );
  const publicMessage = profileMemoryPublicMessage(status, message);

  return (
    <AccessibleModal
      backgroundRef={backgroundRef}
      opener={opener}
      onClose={onClose}
      layerClassName={styles.layer}
      backdropClassName={styles.backdrop}
      dialogClassName={styles.dialog}
      labelledBy="profile-memory-title"
    >
      <header className={styles.header}>
        <div>
          <span>Taste memory</span>
          <h2 id="profile-memory-title">What WatchSignal remembers</h2>
        </div>
        <button type="button" onClick={onClose} aria-label="Close taste memory" autoFocus>
          <WatchSignalIcon name="close" />
        </button>
      </header>

      <div className={styles.scroll}>
        {status === "loading" ? (
          <div className={styles.loading} role="status" aria-live="polite">
            <i /><i />
            <p>{publicMessage}</p>
          </div>
        ) : status === "failed" ? (
          <section className={styles.empty} role="alert">
            <WatchSignalIcon name="refresh" />
            <h3>Taste memory is taking a break</h3>
            <p>{publicMessage}</p>
            <button type="button" onClick={() => void onRetry()}>Try again</button>
          </section>
        ) : snapshots.length === 0 ? (
          <section className={styles.empty}>
            <WatchSignalIcon name="sparkles" />
            <h3>Still learning</h3>
            <p>Movie reactions will build a private taste snapshot here.</p>
          </section>
        ) : (
          <>
            <p className={styles.overlap}>
              <span>Household</span>
              <strong>{householdMemorySummary(snapshots)}</strong>
            </p>
            <div className={styles.profileList}>
              {snapshots.map((snapshot) => {
                const summary = summaries.find((item) => item.profileId === snapshot.profileId)!;
                const recentEvents = events
                  .filter((event) => event.profileId === snapshot.profileId)
                  .slice()
                  .sort((first, second) => second.occurredAt.localeCompare(first.occurredAt))
                  .slice(0, 3);
                return (
                  <article key={snapshot.profileId} className={styles.profile}>
                    <div className={styles.profileLead}>
                      <span aria-hidden="true">{snapshot.label.charAt(0).toUpperCase()}</span>
                      <div>
                        <strong>{snapshot.label}</strong>
                        <p>{snapshot.headline}</p>
                      </div>
                    </div>
                    <p className={styles.caution}>{snapshot.detail}</p>
                    <details>
                      <summary>Why this?</summary>
                      <div className={styles.evidence}>
                        <p>{snapshot.evidenceCount} signals considered</p>
                        <dl>
                          <div><dt>Saved</dt><dd>{summary.savedByProfileCount}</dd></div>
                          <div><dt>Reactions</dt><dd>{summary.recentReactionCount}</dd></div>
                          <div><dt>Watched</dt><dd>{summary.watchedCount}</dd></div>
                          <div><dt>Rated</dt><dd>{summary.ratedCount}</dd></div>
                        </dl>
                        {recentEvents.length > 0 ? (
                          <ul>
                            {recentEvents.map((event) => (
                              <li key={event.eventId}>
                                <span>{event.title}</span>
                                <small>{memoryEventLabel(event)}</small>
                              </li>
                            ))}
                          </ul>
                        ) : <p>No recent movie memories yet.</p>}
                      </div>
                    </details>
                  </article>
                );
              })}
            </div>
          </>
        )}
      </div>

      <footer className={styles.footer}>
        <p>Only household profiles use this memory.</p>
        <button type="button" onClick={onClose}>Done</button>
      </footer>
    </AccessibleModal>
  );
}

function memoryEventLabel(event: TasteMemoryEventPayload): string {
  if (event.eventType === "watchlist_saved") return "Saved for later";
  if (event.eventType === "seen_before") return "Seen before";
  if (event.eventType === "post_watch_feedback") return "After watching";
  if (event.sentimentLabel === "hated" || event.sentimentLabel === "no") return "Not for me";
  if (event.sentimentLabel === "fine" || event.sentimentLabel === "meh") return "It was fine";
  return "Liked";
}
