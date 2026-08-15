"use client";

import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import type {
  PeopleMode,
  RankedCandidate,
  ReactionState,
} from "../../pass-the-phone-model";
import { reactionLabels } from "../../session-fixtures";
import { AccessibleModal } from "../../ui/accessible-modal";
import { WatchSignalIcon } from "../../ui/watchsignal-icons";
import { WatchSignalBrand } from "../../ui/primitives";
import {
  personInitials,
  publicResultSynopsis,
  resultDetailsCast,
  resultEvidence,
  resultProviderPresentation,
  verifiedProviderLaunchUrl,
} from "./result-details-contract";
import styles from "./ranked-result-stage.module.css";

type PosterFallbackHandler = (event: { currentTarget: HTMLImageElement }) => void;

export function RankedResultStage({
  rankedCandidates,
  peopleMode,
  founderReactions,
  wifeReactions,
  sharedReasons,
  continuationOpen,
  continuationContent,
  continuationAvailable = true,
  utilityContent,
  onToggleContinuation,
  onPosterFallback,
}: {
  rankedCandidates: RankedCandidate[];
  peopleMode: PeopleMode;
  founderReactions: ReactionState;
  wifeReactions: ReactionState;
  sharedReasons: Record<string, string>;
  continuationOpen: boolean;
  continuationContent: ReactNode;
  continuationAvailable?: boolean;
  utilityContent: ReactNode;
  onToggleContinuation: () => void;
  onPosterFallback: PosterFallbackHandler;
}) {
  const movies = useMemo(() => rankedCandidates.slice(0, 5), [rankedCandidates]);
  const [activeId, setActiveId] = useState(movies[0]?.id ?? "");
  const [localDialog, setLocalDialog] = useState<"details" | "utility" | null>(null);
  const [availabilityOpen, setAvailabilityOpen] = useState(false);
  const [backdropFailed, setBackdropFailed] = useState(false);
  const backgroundRef = useRef<HTMLDivElement>(null);
  const modalOpenerRef = useRef<HTMLElement | null>(null);
  const activeDialog = continuationOpen ? "continuation" : localDialog;
  const activeIndex = Math.max(0, movies.findIndex((movie) => movie.id === activeId));
  const movie = movies[activeIndex] ?? movies[0];

  useLayoutEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  useEffect(() => {
    if (!movies.some((candidate) => candidate.id === activeId)) {
      setActiveId(movies[0]?.id ?? "");
    }
  }, [activeId, movies]);

  useEffect(() => {
    setBackdropFailed(false);
    setAvailabilityOpen(false);
  }, [movie?.id]);

  if (!movie) {
    return null;
  }

  const nextExactScore = movies[1]?.matchIndex.exactScore;
  const scoreGap =
    nextExactScore === undefined
      ? null
      : movie.matchIndex.exactScore - nextExactScore;
  const leaderGap =
    (movies[0]?.matchIndex.exactScore ?? movie.matchIndex.exactScore) -
    movie.matchIndex.exactScore;
  const reactions = reactionSummary(
    movie.id,
    peopleMode,
    founderReactions,
    wifeReactions,
  );
  const backdropUrl = movie.backdropUrl;
  const providerLaunchUrl = verifiedProviderLaunchUrl(movie.providerUrl);

  function selectMovie(candidate: RankedCandidate) {
    setActiveId(candidate.id);
    setLocalDialog(null);
    setAvailabilityOpen(false);
  }

  function openLocalDialog(
    dialog: "details" | "utility",
    opener: HTMLElement,
  ) {
    modalOpenerRef.current = opener;
    setAvailabilityOpen(false);
    setLocalDialog(dialog);
  }

  function openContinuation(opener: HTMLElement) {
    modalOpenerRef.current = opener;
    setAvailabilityOpen(false);
    setLocalDialog(null);
    if (!continuationOpen) {
      onToggleContinuation();
    }
  }

  function closeActiveDialog() {
    if (activeDialog === "continuation") {
      onToggleContinuation();
      return;
    }
    setLocalDialog(null);
  }

  return (
    <section className={`${styles.stage} goldenResultsStage`} data-watchsignal-results aria-labelledby="ranked-result-title">
      <div ref={backgroundRef} className={styles.stageContent}>
        <div className={styles.fallbackArt} aria-hidden="true"><i /><i /><span>W</span></div>
        {backdropUrl && !backdropFailed ? (
          <img
            key={backdropUrl}
            className={styles.backdrop}
            src={backdropUrl}
            alt=""
            onError={() => setBackdropFailed(true)}
          />
        ) : null}
        <div className={styles.colorWash} aria-hidden="true" />
        <div className={styles.scrim} aria-hidden="true" />

        <header className={styles.header}>
          <WatchSignalBrand />
          <div className={styles.headerEnd}>
            <div className={styles.rank} aria-label={`Rank ${activeIndex + 1} of ${movies.length}`}>
              <strong>{activeIndex + 1}</strong><span>of {movies.length}</span>
            </div>
            <button
              className={styles.moreButton}
              type="button"
              aria-label="More result options"
              aria-expanded={activeDialog === "utility"}
              onClick={(event) => openLocalDialog("utility", event.currentTarget)}
            >
              <span aria-hidden="true">•••</span>
            </button>
          </div>
        </header>

        <div className={styles.body}>
          <div className={styles.signalRow}>
            <ScoreDial score={movie.score} />
            <div>
              <strong>{activeIndex === 0 ? "Tonight’s strongest match" : `Ranked #${activeIndex + 1} tonight`}</strong>
              <span>{activeIndex === 0 ? leadCopy(scoreGap) : trailCopy(leaderGap)}</span>
            </div>
          </div>

          <button
            type="button"
            className={styles.titleBlock}
            onClick={(event) => openLocalDialog("details", event.currentTarget)}
            aria-label={`Open details for ${movie.title}`}
          >
            <h1 id="ranked-result-title">{movie.title}</h1>
            <p>{[movie.year, movie.runtime, ...movie.genres.slice(0, 3)].filter(Boolean).join(" · ")}</p>
            <span><b>{reactions}</b> {sharedReasons[movie.id] ?? compactReason(movie)}</span>
          </button>

          <div className={styles.filmstrip} aria-label="Ranked movies">
            {movies.map((candidate, index) => (
              <button
                key={candidate.id}
                className={candidate.id === movie.id ? styles.activeMovie : undefined}
                type="button"
                onClick={() => selectMovie(candidate)}
                aria-pressed={candidate.id === movie.id}
                aria-label={`${index + 1}. ${candidate.title}, match score ${candidate.score}`}
              >
                <img src={candidate.posterUrl} alt="" onError={onPosterFallback} />
                <span>{candidate.score}</span>
              </button>
            ))}
          </div>

          <div className={styles.dock} role="group" aria-label="Result actions">
            <button type="button" onClick={(event) => openLocalDialog("details", event.currentTarget)}>
              <WatchSignalIcon name="info" /><span>Details</span>
            </button>
            {providerLaunchUrl ? (
              <a className={styles.providerAction} href={providerLaunchUrl} target="_blank" rel="noreferrer">
                <WatchSignalIcon name="play" /><span>Watch</span>
              </a>
            ) : (
              <button className={styles.providerAction} type="button" onClick={() => setAvailabilityOpen(true)}>
                <WatchSignalIcon name="play" /><span>Where to watch</span>
              </button>
            )}
            <button
              type="button"
              onClick={(event) => openContinuation(event.currentTarget)}
              aria-expanded={continuationOpen}
              disabled={!continuationAvailable}
              aria-label={continuationAvailable ? "Find five more movies" : "No fresh local movies remain"}
            >
              <WatchSignalIcon name="refresh" /><span>5 more</span>
            </button>
          </div>
        </div>

        {availabilityOpen ? (
          <div className={styles.availabilityToast} role="status">
            <span><WatchSignalIcon name="play" /></span>
            <div><strong>{movie.availability}</strong><small>Availability is regional. Confirm in your provider app.</small></div>
            <button type="button" onClick={() => setAvailabilityOpen(false)}>Close</button>
          </div>
        ) : null}
      </div>

      {activeDialog === "details" ? (
        <ResultDetailsPreview
          movie={movie}
          backgroundRef={backgroundRef}
          opener={modalOpenerRef.current}
          onClose={closeActiveDialog}
          reactions={reactions}
        />
      ) : null}

      {activeDialog === "continuation" ? (
        <AccessibleModal
          backgroundRef={backgroundRef}
          opener={modalOpenerRef.current}
          onClose={closeActiveDialog}
          layerClassName={styles.sheetLayer}
          backdropClassName={styles.sheetBackdrop}
          dialogClassName={styles.continuationSheet}
          label="Five more options"
        >
            <div className={styles.sheetHeader}><span /><strong>Find five more</strong><button type="button" onClick={onToggleContinuation} aria-label="Close" autoFocus><WatchSignalIcon name="close" /></button></div>
            <div className={styles.sheetScroll}>{continuationContent}</div>
        </AccessibleModal>
      ) : null}

      {activeDialog === "utility" ? (
        <AccessibleModal
          backgroundRef={backgroundRef}
          opener={modalOpenerRef.current}
          onClose={closeActiveDialog}
          layerClassName={styles.sheetLayer}
          backdropClassName={styles.sheetBackdrop}
          dialogClassName={styles.utilitySheet}
          label="Result options"
        >
            <div className={styles.sheetHeader}><span /><strong>Tonight’s result</strong><button type="button" onClick={closeActiveDialog} aria-label="Close" autoFocus><WatchSignalIcon name="close" /></button></div>
            <div className={styles.sheetScroll}>{utilityContent}</div>
        </AccessibleModal>
      ) : null}
    </section>
  );
}

function ResultDetailsPreview({
  movie,
  backgroundRef,
  opener,
  onClose,
  reactions,
}: {
  movie: RankedCandidate;
  backgroundRef: RefObject<HTMLElement | null>;
  opener: HTMLElement | null;
  onClose: () => void;
  reactions: string;
}) {
  const cast = resultDetailsCast(movie);
  const evidence = resultEvidence({
    reactions,
    tone: movie.tone,
    runtime: movie.runtime,
  });
  const provider = resultProviderPresentation({
    providerAvailability: movie.providerAvailability,
    fallbackAvailability: movie.availability,
  });
  const providerLaunchUrl = verifiedProviderLaunchUrl(movie.providerUrl);

  return (
    <AccessibleModal
      backgroundRef={backgroundRef}
      opener={opener}
      onClose={onClose}
      layerClassName={styles.sheetLayer}
      backdropClassName={styles.sheetBackdrop}
      dialogClassName={styles.detailsSheet}
      labelledBy="result-details-title"
    >
      <div className={styles.detailsHandle} aria-hidden="true" />
      <header className={styles.detailsHeader}>
        <DetailsPoster src={movie.posterUrl} />
        <div>
          <p>{movie.year} · {movie.runtime}</p>
          <h2 id="result-details-title">{movie.title}</h2>
          <span>{movie.genres.join(" · ")}</span>
        </div>
        <button type="button" onClick={onClose} aria-label="Close movie details" autoFocus>
          <WatchSignalIcon name="close" />
        </button>
      </header>

      <div className={styles.detailsScroll}>
        <section className={styles.detailsSection}>
          <h3>What it’s about</h3>
          <p>{publicResultSynopsis(movie)}</p>
        </section>

        <section className={styles.detailsSection}>
          <h3>Who’s in it</h3>
          {cast.length > 0 ? (
            <div className={styles.castList}>
              {cast.map((person) => (
                <CastMember key={person.name} person={person} />
              ))}
            </div>
          ) : (
            <p className={styles.missingDetails}>Cast details are not available for this title yet.</p>
          )}
        </section>

        <section className={styles.whyDetails} aria-label={`Why match score ${movie.score}`}>
          <header><h3>Why {movie.score}</h3><span>{stripPeriod(reactions)}</span></header>
          <ul>
            {evidence.map((item) => (
              <li key={item}><WatchSignalIcon name="check" /><span>{item}</span></li>
            ))}
          </ul>
        </section>

        <section className={styles.providerDetails} aria-label="German watch availability">
          <div className={styles.providerMark}><WatchSignalIcon name="play" /></div>
          <div>
            <strong>{provider.providerLabel}</strong>
            <span>{provider.accessLabel} · {provider.regionLabel}</span>
            <small>{movie.languageAccess}</small>
          </div>
          {providerLaunchUrl ? (
            <a href={providerLaunchUrl} target="_blank" rel="noreferrer">
              Watch <WatchSignalIcon name="chevron-right" />
            </a>
          ) : null}
        </section>

        <p className={styles.dataCredit}>Movie metadata and imagery from TMDB · Availability region DE</p>
      </div>
    </AccessibleModal>
  );
}

function DetailsPoster({ src }: { src: string }) {
  const [failed, setFailed] = useState(false);
  return failed || !src ? (
    <div className={styles.detailsPosterFallback} aria-hidden="true">W</div>
  ) : (
    <img className={styles.detailsPoster} src={src} alt="" onError={() => setFailed(true)} />
  );
}

function CastMember({
  person,
}: {
  person: ReturnType<typeof resultDetailsCast>[number];
}) {
  const [profileFailed, setProfileFailed] = useState(false);
  return (
    <article>
      <div className={styles.castPortrait}>
        {person.profileUrl && !profileFailed ? (
          <img src={person.profileUrl} alt="" onError={() => setProfileFailed(true)} />
        ) : (
          <span aria-hidden="true">{personInitials(person.name)}</span>
        )}
      </div>
      <strong>{person.name}</strong>
      <span>{person.character ?? "Cast"}</span>
    </article>
  );
}

function stripPeriod(value: string): string {
  return value.replace(/[.!?]+$/, "");
}

function ScoreDial({ score }: { score: number }) {
  return (
    <div className={styles.scoreDial} aria-label={`Match score ${score} out of 100`}>
      <svg viewBox="0 0 58 58" aria-hidden="true"><circle cx="29" cy="29" r="25" /><circle className={styles.scoreArc} cx="29" cy="29" r="25" pathLength="100" strokeDasharray="100" strokeDashoffset={100 - score} /></svg>
      <span><strong>{score}</strong><small>match</small></span>
    </div>
  );
}

function reactionSummary(
  candidateId: string,
  peopleMode: PeopleMode,
  founderReactions: ReactionState,
  wifeReactions: ReactionState,
): string {
  if (peopleMode === "couple") {
    const founder = founderReactions[candidateId];
    const wife = wifeReactions[candidateId];
    if (founder === "interested" && wife === "interested") return "Both interested.";
    if (founder && wife && founder === wife) return `Both ${reactionLabels[founder].toLowerCase()}.`;
    if (founder && wife) return `${reactionLabels[founder]} + ${reactionLabels[wife].toLowerCase()}.`;
    return "Shared signal.";
  }

  const reaction = peopleMode === "founder" ? founderReactions[candidateId] : wifeReactions[candidateId];
  return reaction ? `${reactionLabels[reaction]}.` : "Your strongest signal.";
}

function compactReason(movie: RankedCandidate): string {
  const source = movie.tone || movie.reason;
  return source.length > 92 ? `${source.slice(0, 89).trimEnd()}…` : source.replace(/[.!?]?$/, ".");
}

function leadCopy(gap: number | null): string {
  if (gap === null) {
    return "Only match";
  }
  if (Math.abs(gap) <= Number.EPSILON) {
    return "Tied on match signal";
  }
  if (gap > 0 && gap < 1) {
    return "<1 point clear";
  }
  return `${Math.floor(gap)} points clear`;
}

function trailCopy(gap: number): string {
  if (Math.abs(gap) <= Number.EPSILON) {
    return "Tied on match signal";
  }
  if (gap > 0 && gap < 1) {
    return "<1 point behind #1";
  }
  if (gap > 0) {
    return `${Math.floor(gap)} points behind #1`;
  }
  return "Local signal differs from the shared rank";
}
