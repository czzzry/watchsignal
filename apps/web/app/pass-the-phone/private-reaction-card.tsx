"use client";

import { useEffect, useRef, useState } from "react";
import type { DemoCandidate, ReactionValue } from "../session-fixtures";
import { reactionLabels } from "../session-fixtures";
import type { SeenMemoryValue } from "../pass-the-phone-model";
import { AccessibleModal } from "../ui/accessible-modal";
import { WatchSignalIcon, type WatchSignalIconName } from "../ui/watchsignal-icons";
import { WatchSignalBrand } from "../ui/primitives";
import {
  canBeginPrivateReaction,
  publicReactionFitLine,
  publicReactionSynopsis,
  privateReactionStatus,
  privateReactionValues,
} from "./reaction-card-contract";
import {
  seenMemoryConfirmationLabel,
  seenMemoryOptions,
  type SeenMemorySaveResult,
} from "./seen-memory-contract";
import { SeenMemoryDialog } from "./seen-memory-dialog";
import styles from "./private-reaction-card.module.css";

const seenMemoryLabels = Object.fromEntries(
  seenMemoryOptions.map((option) => [option.value, option.label]),
) as Record<SeenMemoryValue, string>;

export function PrivateReactionCard({
  actorLabel,
  actorAvatarKey,
  actorColorKey,
  actor,
  index,
  total,
  candidate,
  selectedReaction,
  seenMemory,
  isSyncing,
  localOnly,
  sessionNotice,
  onReaction,
  onSeenIt,
  onBack,
}: {
  actorLabel: string;
  actorAvatarKey: string;
  actorColorKey: string;
  actor: "founder" | "wife";
  index: number;
  total: number;
  candidate: DemoCandidate;
  selectedReaction: ReactionValue | undefined;
  seenMemory: SeenMemoryValue | undefined;
  isSyncing: boolean;
  localOnly: boolean;
  sessionNotice?: string | null;
  onReaction: (
    actor: "founder" | "wife",
    candidateId: string,
    reaction: ReactionValue,
  ) => void | Promise<void>;
  onSeenIt: (memory: SeenMemoryValue) => Promise<SeenMemorySaveResult>;
  onBack: () => void;
}) {
  const [posterFailed, setPosterFailed] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [detailsOpener, setDetailsOpener] = useState<HTMLElement | null>(null);
  const [seenMemoryOpen, setSeenMemoryOpen] = useState(false);
  const [seenMemoryOpener, setSeenMemoryOpener] = useState<HTMLElement | null>(null);
  const [pendingReaction, setPendingReaction] = useState<ReactionValue | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);
  const commitLockedRef = useRef(false);
  const lastAcceptedAtRef = useRef(Number.NEGATIVE_INFINITY);
  const backgroundRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setPosterFailed(false);
    setDetailsOpen(false);
    setDetailsOpener(null);
    setSeenMemoryOpen(false);
    setSeenMemoryOpener(null);
    setPendingReaction(null);
    setCommitError(null);
  }, [candidate.id]);

  const activeReaction = pendingReaction ?? selectedReaction;
  const status = privateReactionStatus({ pending: pendingReaction, isSyncing, localOnly });
  const visibleStatus = pendingReaction || isSyncing ? status : sessionNotice ?? status;
  const fitLine = publicReactionFitLine(candidate);
  const synopsis = publicReactionSynopsis(candidate);
  const showPoster = Boolean(candidate.posterUrl) && !posterFailed;

  async function commitReaction(reaction: ReactionValue): Promise<void> {
    const now = window.performance.now();
    if (!canBeginPrivateReaction({
      commitLocked: commitLockedRef.current,
      isSyncing,
      lastAcceptedAt: lastAcceptedAtRef.current,
      now,
    })) {
      return;
    }

    commitLockedRef.current = true;
    lastAcceptedAtRef.current = now;
    setPendingReaction(reaction);
    setCommitError(null);

    try {
      await onReaction(actor, candidate.id, reaction);
    } catch {
      setCommitError("Your pick wasn’t saved. Try once more.");
    } finally {
      commitLockedRef.current = false;
      setPendingReaction(null);
    }
  }

  function openDetails(opener: HTMLElement): void {
    setDetailsOpener(opener);
    setDetailsOpen(true);
  }

  return (
    <section className={styles.stage} data-reaction-stage aria-labelledby="private-reaction-title">
      <div ref={backgroundRef} className={styles.stageContent}>
        <header className={styles.header}>
          <button
            type="button"
            className={styles.backButton}
            onClick={onBack}
            disabled={isSyncing || pendingReaction !== null}
            aria-label="Back"
          >
            <WatchSignalIcon name="arrow-left" />
          </button>

          <div className={styles.identity} data-color={actorColorKey}>
            <span aria-hidden="true">{avatarSymbol(actorAvatarKey)}</span>
            <div><strong>{actorLabel}</strong><small>Private pick</small></div>
          </div>

          <div className={styles.progress} aria-label={`Movie ${index + 1} of ${total}`}>
            <strong>{index + 1}</strong><span>of {total}</span>
          </div>
        </header>

        <div className={styles.progressTrack} aria-hidden="true">
          <span style={{ transform: `scaleX(${Math.min(1, (index + 1) / Math.max(1, total))})` }} />
        </div>

        <main className={styles.cardArea}>
          <article className={styles.movieCard} data-pending={pendingReaction !== null || undefined}>
            <div className={styles.posterFallback} aria-hidden={showPoster || undefined}>
              <WatchSignalBrand compact />
              <span>{candidate.title}</span>
            </div>
            {showPoster ? (
              <img
                key={candidate.posterUrl}
                className={styles.poster}
                src={candidate.posterUrl}
                alt=""
                onError={() => setPosterFailed(true)}
              />
            ) : null}
            <div className={styles.posterScrim} aria-hidden="true" />

            <div className={styles.movieCopy}>
              <h1 id="private-reaction-title">{candidate.title}</h1>
              <p className={styles.meta}>
                {[candidate.year, candidate.runtime, ...candidate.genres.slice(0, 3)].filter(Boolean).join(" · ")}
              </p>
              <p className={styles.fitLine}>{fitLine}</p>
              <div className={styles.movieActions}>
                <button type="button" onClick={(event) => openDetails(event.currentTarget)}>
                  <WatchSignalIcon name="info" />Details
                </button>
                <button
                  type="button"
                  onClick={(event) => {
                    setSeenMemoryOpener(event.currentTarget);
                    setSeenMemoryOpen(true);
                  }}
                  disabled={isSyncing || pendingReaction !== null}
                  aria-label={seenMemory ? `Seen before, ${seenMemoryLabels[seenMemory]}. ${seenMemoryConfirmationLabel(localOnly)}` : "Seen before"}
                >
                  <WatchSignalIcon name={seenMemory ? "check" : "history"} />
                  {seenMemory ? seenMemoryConfirmationLabel(localOnly) : "Seen before"}
                </button>
              </div>
            </div>

            {pendingReaction ? (
              <div className={styles.lockIn} role="status" aria-live="polite">
                <WatchSignalIcon name="check" />
                <strong>{reactionLabels[pendingReaction]}</strong>
              </div>
            ) : null}
          </article>
        </main>

        <footer className={styles.reactionDock}>
          <p className={styles.prompt}>Would you watch this tonight?</p>
          <div className={styles.reactionChoices} role="group" aria-label={`Private reaction for ${candidate.title}`}>
            {privateReactionValues.map((reaction) => (
              <button
                key={reaction}
                type="button"
                data-reaction={reaction}
                data-selected={activeReaction === reaction || undefined}
                aria-pressed={activeReaction === reaction}
                disabled={isSyncing || pendingReaction !== null}
                onClick={() => void commitReaction(reaction)}
              >
                <WatchSignalIcon name={reactionIcon(reaction)} />
                <span>{reactionLabels[reaction]}</span>
              </button>
            ))}
          </div>
          <p className={styles.privateStatus} data-error={commitError ? "true" : undefined} role={commitError ? "alert" : "status"} aria-live="polite">
            {commitError ?? visibleStatus}
          </p>
        </footer>
      </div>

      {detailsOpen ? (
        <AccessibleModal
          backgroundRef={backgroundRef}
          opener={detailsOpener}
          onClose={() => setDetailsOpen(false)}
          layerClassName={styles.detailsLayer}
          backdropClassName={styles.detailsBackdrop}
          dialogClassName={styles.detailsSheet}
          labelledBy="private-movie-details-title"
        >
          <header className={styles.sheetHeader}>
            <span aria-hidden="true" />
            <div><small>Movie details</small><h2 id="private-movie-details-title">{candidate.title}</h2></div>
            <button type="button" onClick={() => setDetailsOpen(false)} aria-label="Close movie details" autoFocus>
              <WatchSignalIcon name="close" />
            </button>
          </header>
          <div className={styles.sheetBody}>
            <section>
              <h3>What it’s about</h3>
              <p>{synopsis}</p>
            </section>
            <section>
              <h3>Who’s in it</h3>
              {candidate.topCast.length > 0 ? (
                <ul>{candidate.topCast.slice(0, 3).map((name) => <li key={name}>{name}</li>)}</ul>
              ) : (
                <p>Cast information isn’t available for this title.</p>
              )}
            </section>
            <section>
              <h3>Access</h3>
              <p>{candidate.availability || "Provider availability needs a quick check."}</p>
              <small>{candidate.languageAccess || "Language access isn’t confirmed."}</small>
            </section>
            <p className={styles.attribution}>Movie metadata and imagery from TMDB</p>
          </div>
        </AccessibleModal>
      ) : null}

      {seenMemoryOpen ? (
        <SeenMemoryDialog
          actorLabel={actorLabel}
          candidate={candidate}
          initialValue={seenMemory}
          localOnly={localOnly}
          isSaving={isSyncing}
          backgroundRef={backgroundRef}
          opener={seenMemoryOpener}
          onSave={onSeenIt}
          onClose={() => setSeenMemoryOpen(false)}
        />
      ) : null}
    </section>
  );
}

function reactionIcon(reaction: ReactionValue): WatchSignalIconName {
  if (reaction === "interested") return "heart";
  if (reaction === "maybe") return "sparkles";
  return "close";
}

function avatarSymbol(avatarKey: string): string {
  return ({ spark: "S", moon: "M", comet: "C", ticket: "T" } as Record<string, string>)[avatarKey] ?? "P";
}
