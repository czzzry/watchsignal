import type { ReactionState } from "../pass-the-phone-model";
import type { DemoCandidate } from "../session-fixtures";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import styles from "./private-reaction-card.module.css";

type PosterRailStatus = "done" | "deferred" | "upcoming";

export function PrivateReactionPosterRail({
  candidates,
  reactions,
  activeCandidateId,
  deferredCandidateIds,
  hasForwardCandidate,
}: {
  candidates: DemoCandidate[];
  reactions: ReactionState;
  activeCandidateId: string;
  deferredCandidateIds: string[];
  hasForwardCandidate: boolean;
}) {
  const deferred = new Set(deferredCandidateIds);
  const states = candidates.map((candidate) => ({
    candidate,
    active: candidate.id === activeCandidateId,
    status: posterRailStatus(candidate.id, reactions, deferred),
  }));

  return (
    <section
      className={styles.posterRailSection}
      aria-labelledby="private-reaction-rail-title"
      aria-describedby="private-reaction-rail-summary"
    >
      <div className={styles.posterRailHeader}>
        <h2 id="private-reaction-rail-title">Tonight&apos;s five</h2>
        <span>{hasForwardCandidate ? "Swipe left for next" : "Swipe left to skip for now"}</span>
      </div>
      <p id="private-reaction-rail-summary" className={styles.screenReaderOnly}>
        {states.map(({ candidate, status, active }) =>
          posterRailLabel(candidate.title, status, active)
        ).join(". ")}
      </p>
      <ol className={styles.posterRail} role="list" aria-label="Five movies in this round">
        {states.map(({ candidate, status, active }) => (
          <li
            key={candidate.id}
            className={styles.posterRailItem}
            role="listitem"
            data-active={active || undefined}
            data-status={status}
            aria-current={active ? "step" : undefined}
            aria-label={posterRailLabel(candidate.title, status, active)}
          >
            <span className={styles.posterRailFallback} aria-hidden="true">
              {candidate.title.slice(0, 1)}
            </span>
            {candidate.posterUrl ? (
              <img
                src={candidate.posterUrl}
                alt=""
                onError={(event) => {
                  event.currentTarget.hidden = true;
                }}
              />
            ) : null}
            {status === "done" ? (
              <span className={styles.posterRailMark} aria-hidden="true">
                <WatchSignalIcon name="check" />
              </span>
            ) : null}
            {status === "deferred" ? (
              <span className={styles.posterRailMark} aria-hidden="true">
                <WatchSignalIcon name="refresh" />
              </span>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}

function posterRailStatus(
  candidateId: string,
  reactions: ReactionState,
  deferredCandidateIds: ReadonlySet<string>,
): PosterRailStatus {
  if (reactions[candidateId]) return "done";
  return deferredCandidateIds.has(candidateId) ? "deferred" : "upcoming";
}

function posterRailLabel(
  title: string,
  status: PosterRailStatus,
  active: boolean,
): string {
  const statusLabel = status === "done"
    ? "answered"
    : status === "deferred" ? "skipped once" : "not answered yet";
  return `${title}, ${active ? "current movie, " : ""}${statusLabel}`;
}
