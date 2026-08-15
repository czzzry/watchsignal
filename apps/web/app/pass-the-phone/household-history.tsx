"use client";

import { useState, type RefObject } from "react";
import type { DebugHistoryStatus } from "../pass-the-phone-model";
import type {
  HouseholdHistoryDetailPayload,
  HouseholdHistorySummaryPayload,
} from "../session-client";
import { AccessibleModal } from "../ui/accessible-modal";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import {
  householdHistoryDetail,
  historyPublicMessage,
  recentNightSummary,
} from "./household-history-contract";
import styles from "./household-history.module.css";

export function HouseholdHistory({
  backgroundRef,
  opener,
  sessions,
  status,
  message,
  selectedHistory,
  selectedHistoryStatus,
  selectedHistoryMessage,
  onLoad,
  onSelect,
  onClose,
}: {
  backgroundRef: RefObject<HTMLElement | null>;
  opener: HTMLElement | null;
  sessions: HouseholdHistorySummaryPayload[];
  status: DebugHistoryStatus;
  message: string | null;
  selectedHistory: HouseholdHistoryDetailPayload | null;
  selectedHistoryStatus: DebugHistoryStatus;
  selectedHistoryMessage: string | null;
  onLoad: () => void | Promise<void>;
  onSelect: (sessionId: string) => void | Promise<void>;
  onClose: () => void;
}) {
  const [detailSessionId, setDetailSessionId] = useState<string | null>(null);
  const publicListMessage = historyPublicMessage(status, message);
  const publicDetailMessage = historyPublicMessage(selectedHistoryStatus, selectedHistoryMessage);
  const detail = selectedHistory && detailSessionId
    ? householdHistoryDetail(selectedHistory)
    : null;

  async function openDetail(sessionId: string): Promise<void> {
    setDetailSessionId(sessionId);
    await onSelect(sessionId);
  }

  return (
    <AccessibleModal
      backgroundRef={backgroundRef}
      opener={opener}
      onClose={onClose}
      layerClassName={styles.layer}
      backdropClassName={styles.backdrop}
      dialogClassName={styles.dialog}
      labelledBy="household-history-title"
      focusReturnTiming="synchronous"
    >
      <header className={styles.header}>
        {detailSessionId ? (
          <button type="button" onClick={() => setDetailSessionId(null)} aria-label="Back to recent nights" autoFocus>
            <WatchSignalIcon name="arrow-left" />
          </button>
        ) : <span className={styles.headerMark}><WatchSignalIcon name="history" /></span>}
        <div>
          <span>{detailSessionId ? "Night details" : "Household"}</span>
          <h2 id="household-history-title">{detailSessionId ? detail?.chosenTitle ?? "Loading…" : "Recent nights"}</h2>
        </div>
        <button type="button" onClick={onClose} aria-label="Close recent nights" autoFocus={!detailSessionId}>
          <WatchSignalIcon name="close" />
        </button>
      </header>

      <div className={styles.scroll}>
        {detailSessionId ? (
          selectedHistoryStatus === "loading" ? (
            <HistoryLoading label="Loading night details…" />
          ) : selectedHistoryStatus === "failed" ? (
            <HistoryFailure message={publicDetailMessage} onRetry={() => openDetail(detailSessionId)} />
          ) : detail ? (
            <section className={styles.detail}>
              <HistoryPoster
                className={styles.detailPoster}
                title={detail.chosenTitle}
                posterUrl={detail.posterUrl}
              />
              <div className={styles.detailLead}>
                <span>{detail.outcome ?? "Tonight’s strongest match"}</span>
                <h3>{detail.chosenTitle}</h3>
              </div>
              {detail.feedback.length > 0 ? (
                <p className={styles.feedback}>{detail.feedback.join(" · ")}</p>
              ) : null}
              {detail.alternatives.length > 0 ? (
                <section className={styles.alternatives}>
                  <h4>Other picks that night</h4>
                  <ul>{detail.alternatives.map((movie) => <li key={movie.title}>{movie.title}</li>)}</ul>
                </section>
              ) : null}
            </section>
          ) : null
        ) : status === "loading" || status === "idle" ? (
          <HistoryLoading label={publicListMessage ?? "Loading recent nights…"} />
        ) : status === "failed" ? (
          <HistoryFailure message={publicListMessage} onRetry={onLoad} />
        ) : sessions.length === 0 ? (
          <section className={styles.empty}>
            <WatchSignalIcon name="history" />
            <h3>No recent nights yet</h3>
            <p>Your shared picks will appear here after a saved movie night.</p>
          </section>
        ) : (
          <div className={styles.list}>
            {sessions.map((session) => {
              const item = recentNightSummary(session);
              return (
                <button key={session.historyHandle} type="button" onClick={() => void openDetail(session.historyHandle)}>
                  <HistoryPoster
                    className={styles.miniPoster}
                    title={item.title}
                    posterUrl={session.posterUrl}
                  />
                  <span className={styles.itemCopy}>
                    <small>{item.date}</small>
                    <strong>{item.title}</strong>
                    <span>{item.outcome}</span>
                  </span>
                  <WatchSignalIcon name="chevron-right" />
                </button>
              );
            })}
          </div>
        )}
      </div>

      <footer className={styles.footer}>
        {detailSessionId ? (
          <button type="button" onClick={() => setDetailSessionId(null)}>Back to recent nights</button>
        ) : (
          <button type="button" onClick={onClose}>Done</button>
        )}
      </footer>
    </AccessibleModal>
  );
}

function HistoryPoster({
  className,
  title,
  posterUrl,
}: {
  className: string;
  title: string;
  posterUrl: string | null;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <span className={className}>
      {posterUrl && !failed ? (
        <img src={posterUrl} alt="" onError={() => setFailed(true)} />
      ) : (
        <i aria-label={`${title} poster unavailable`}><WatchSignalIcon name="film" /></i>
      )}
    </span>
  );
}

function HistoryLoading({ label }: { label: string }) {
  return <div className={styles.loading} role="status" aria-live="polite"><i /><i /><i /><p>{label}</p></div>;
}

function HistoryFailure({ message, onRetry }: { message: string | null; onRetry: () => void | Promise<void> }) {
  return (
    <section className={styles.empty} role="alert">
      <WatchSignalIcon name="refresh" />
      <h3>Recent nights are out of reach</h3>
      <p>{message}</p>
      <button type="button" onClick={() => void onRetry()}>Try again</button>
    </section>
  );
}
