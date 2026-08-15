"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  getTasteLabProfiles,
  getTasteLabQueue,
  getTasteLabRatings,
  seedDefaultTasteLabCandidates,
  submitTasteLabRatings,
  type SetupProfilePayload,
  type TasteLabCandidatePayload,
  type TasteLabRatingExportPayload,
  type TasteLabRatingInputPayload,
  type TasteLabRatingLabel,
} from "../taste-lab-client";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import { WatchSignalBrand } from "../ui/primitives";
import {
  tasteLabChoiceGroups,
  tasteLabQueueState,
  type TasteLabQueueState,
} from "./taste-lab-contract";
import styles from "./taste-lab.module.css";

const householdId = "default-household";
const fallbackProfileId = "profile-1";
const fallbackProfiles: SetupProfilePayload[] = [
  { id: "profile-1", label: "Husband", order: 1, avatarKey: "spark", colorKey: "cyan" },
  { id: "profile-2", label: "Wife", order: 2, avatarKey: "moon", colorKey: "rose" },
];

type DraftsByProfile = Record<string, Record<string, TasteLabRatingLabel>>;

export default function TasteLabPage() {
  const [profiles, setProfiles] = useState<SetupProfilePayload[]>(fallbackProfiles);
  const [profileId, setProfileId] = useState(fallbackProfileId);
  const [queue, setQueue] = useState<TasteLabCandidatePayload[]>([]);
  const [draftsByProfile, setDraftsByProfile] = useState<DraftsByProfile>({});
  const [historyByProfile, setHistoryByProfile] = useState<
    Record<string, TasteLabRatingExportPayload[]>
  >({});
  const [queueState, setQueueState] = useState<TasteLabQueueState>("loading");
  const [status, setStatus] = useState("Loading your next movies…");
  const [busy, setBusy] = useState(false);
  const [batchTotal, setBatchTotal] = useState(0);
  const [batchAnswered, setBatchAnswered] = useState(0);
  const [posterFailed, setPosterFailed] = useState(false);
  const [readyPosterMovieId, setReadyPosterMovieId] = useState<string | null>(null);
  const requestIdRef = useRef(0);
  const activeTitleRef = useRef<HTMLHeadingElement>(null);

  const activeProfile = profiles.find((profile) => profile.id === profileId) ?? profiles[0];
  const history = historyByProfile[profileId] ?? [];
  const activeCandidate = queue[0] ?? null;
  const selectedLabel = activeCandidate
    ? draftsByProfile[profileId]?.[activeCandidate.movie.sourceMovieId]
    : undefined;
  const importableCount = history.filter((rating) => rating.isImportablePreference).length;
  const familiarityCount = history.length - importableCount;
  const coverage = useMemo(() => {
    const genres = new Set<string>();
    history.forEach((rating) => rating.movie.genres.forEach((genre) => genres.add(genre)));
    return genres.size;
  }, [history]);
  const isLocal = queueState === "local" || queueState === "local-exhausted";
  const progressPosition = Math.min(batchTotal, batchAnswered + (activeCandidate ? 1 : 0));

  useEffect(() => {
    void loadProfiles();
  }, []);

  useEffect(() => {
    void refresh(profileId);
    return () => {
      requestIdRef.current += 1;
    };
  }, [profileId]);

  useEffect(() => {
    setPosterFailed(false);
    setReadyPosterMovieId(null);
    if (activeCandidate) {
      requestAnimationFrame(() => activeTitleRef.current?.focus());
    }
  }, [activeCandidate?.movie.sourceMovieId]);

  async function loadProfiles(): Promise<void> {
    try {
      const setup = await getTasteLabProfiles();
      const sortedProfiles = [...setup.profiles].sort((first, second) => first.order - second.order);
      if (sortedProfiles.length === 0) return;
      setProfiles(sortedProfiles);
      setProfileId(
        setup.activeProfileId && sortedProfiles.some((profile) => profile.id === setup.activeProfileId)
          ? setup.activeProfileId
          : sortedProfiles[0].id,
      );
    } catch {
      setProfiles(fallbackProfiles);
    }
  }

  async function refresh(nextProfileId = profileId): Promise<void> {
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setBusy(true);
    setQueue([]);
    setBatchTotal(0);
    setBatchAnswered(0);
    setQueueState("loading");
    setStatus("Loading your next movies…");
    try {
      const [nextQueue, savedRatings] = await Promise.all([
        getTasteLabQueue(householdId, nextProfileId, 10),
        getTasteLabRatings(householdId, nextProfileId),
      ]);
      if (requestIdRef.current !== requestId) return;
      setQueue(nextQueue);
      setHistoryByProfile((current) => ({ ...current, [nextProfileId]: savedRatings }));
      setBatchTotal(nextQueue.length);
      setBatchAnswered(0);
      setQueueState(tasteLabQueueState(nextQueue.length, savedRatings.length, false));
      setStatus(
        nextQueue.length > 0
          ? `Ready for ${profileLabel(nextProfileId, profiles)}.`
          : savedRatings.length > 0
            ? "You’ve answered every movie currently available."
            : "No movies are ready yet.",
      );
    } catch {
      if (requestIdRef.current !== requestId) return;
      const savedRatings = historyByProfile[nextProfileId] ?? [];
      const nextQueue = localDemoQueue(savedRatings);
      setQueue(nextQueue);
      setBatchTotal(nextQueue.length);
      setBatchAnswered(0);
      setQueueState(tasteLabQueueState(nextQueue.length, savedRatings.length, true));
      setStatus(
        nextQueue.length > 0
          ? "Using built-in movies. Choices stay on this phone until you reconnect."
          : "Taste Lab is offline and there are no built-in movies left.",
      );
    } finally {
      if (requestIdRef.current === requestId) setBusy(false);
    }
  }

  async function seedQueue(): Promise<void> {
    setBusy(true);
    setQueueState("loading");
    setStatus("Preparing your first movies…");
    try {
      await seedDefaultTasteLabCandidates(householdId);
      await refresh(profileId);
    } catch {
      const nextQueue = localDemoQueue(history);
      setQueue(nextQueue);
      setBatchTotal(nextQueue.length);
      setBatchAnswered(0);
      setQueueState(tasteLabQueueState(nextQueue.length, history.length, true));
      setStatus(
        nextQueue.length > 0
          ? "Using built-in movies. Choices stay on this phone until you reconnect."
          : "Couldn’t prepare movies. Try again when you’re connected.",
      );
      setBusy(false);
    }
  }

  function choose(label: TasteLabRatingLabel): void {
    if (!activeCandidate || busy) return;
    setDraftsByProfile((current) => ({
      ...current,
      [profileId]: {
        ...(current[profileId] ?? {}),
        [activeCandidate.movie.sourceMovieId]: label,
      },
    }));
    setStatus(label === "havent_seen" ? "Marked as not seen. This is not a taste vote." : "Choice ready to save.");
  }

  async function saveAndNext(): Promise<void> {
    if (!activeCandidate || !selectedLabel || busy) return;
    if (isLocal) {
      keepCurrentChoiceLocally();
      return;
    }

    const rating = ratingInput(activeCandidate, selectedLabel);
    setBusy(true);
    setQueueState("saving");
    setStatus(`Saving ${activeCandidate.movie.title}…`);
    try {
      const saved = await submitTasteLabRatings(householdId, profileId, [rating]);
      commitCurrentChoice(saved, false);
    } catch {
      setQueueState("error");
      setStatus("Couldn’t save. Your choice is still here.");
    } finally {
      setBusy(false);
    }
  }

  function keepCurrentChoiceLocally(): void {
    if (!activeCandidate || !selectedLabel) return;
    const savedAt = new Date().toISOString();
    const local = localRatingExport(
      householdId,
      profileId,
      ratingInput(activeCandidate, selectedLabel),
      savedAt,
    );
    commitCurrentChoice([local], true);
  }

  function commitCurrentChoice(
    saved: TasteLabRatingExportPayload[],
    local: boolean,
  ): void {
    if (!activeCandidate) return;
    const movieId = activeCandidate.movie.sourceMovieId;
    const nextQueue = queue.filter((candidate) => candidate.movie.sourceMovieId !== movieId);
    setHistoryByProfile((current) => {
      const profileHistory = current[profileId] ?? [];
      return {
        ...current,
        [profileId]: [
          ...saved,
          ...profileHistory.filter(
            (item) => !saved.some((next) => next.movie.sourceMovieId === item.movie.sourceMovieId),
          ),
        ],
      };
    });
    setDraftsByProfile((current) => {
      const nextProfileDrafts = { ...(current[profileId] ?? {}) };
      delete nextProfileDrafts[movieId];
      return { ...current, [profileId]: nextProfileDrafts };
    });
    setQueue(nextQueue);
    setBatchAnswered((current) => current + 1);
    setQueueState(nextQueue.length > 0 ? (local ? "local" : "ready") : (local ? "local-exhausted" : "batch-complete"));
    setStatus(
      nextQueue.length > 0
        ? local
          ? "Kept on this phone. Next movie."
          : "Saved. Next movie."
        : local
          ? "Built-in batch complete. These choices are only on this phone."
          : "Batch complete. Check for another set when you’re ready.",
    );
  }

  return (
    <main className={styles.shell}>
      <header className={styles.topbar}>
        <a href="/" aria-label="Back to WatchSignal"><WatchSignalBrand /></a>
        <span>Private Taste Lab</span>
      </header>

      <section className={styles.profileBar} aria-label="Whose taste profile">
        <div className={styles.profileIdentity}>
          <span aria-hidden="true">{activeProfile?.label.charAt(0).toUpperCase() ?? "P"}</span>
          <label>
            <small>Learning for</small>
            <select
              value={profileId}
              onChange={(event) => setProfileId(event.target.value)}
              disabled={busy}
              aria-label="Taste Lab profile"
            >
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>{profile.label}</option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {activeCandidate ? (
        <>
          <section className={styles.progress} aria-label={`Movie ${progressPosition} of ${batchTotal}`}>
            <div><span>Tonight’s taste check</span><strong>{progressPosition} of {batchTotal}</strong></div>
            <i><span style={{ width: `${batchTotal ? (progressPosition / batchTotal) * 100 : 0}%` }} /></i>
          </section>

          <article className={styles.decision} aria-labelledby="taste-lab-movie-title">
            <div className={styles.poster}>
              {activeCandidate.movie.posterPath && !posterFailed ? (
                <>
                  {readyPosterMovieId !== activeCandidate.movie.sourceMovieId ? (
                    <div className={styles.posterLoading} role="status" aria-label={`${activeCandidate.movie.title} poster loading`}>
                      <span>W</span><small>Loading poster</small>
                    </div>
                  ) : null}
                  <img
                    key={activeCandidate.movie.sourceMovieId}
                    src={posterUrl(activeCandidate.movie.posterPath)}
                    alt=""
                    hidden={readyPosterMovieId !== activeCandidate.movie.sourceMovieId}
                    onLoad={() => setReadyPosterMovieId(activeCandidate.movie.sourceMovieId)}
                    onError={() => setPosterFailed(true)}
                  />
                </>
              ) : (
                <div aria-label={`${activeCandidate.movie.title} poster unavailable`}>
                  <span>W</span><small>Poster unavailable</small>
                </div>
              )}
            </div>
            <div className={styles.movieCopy}>
              <span>{[activeCandidate.movie.releaseYear, ...activeCandidate.movie.genres.slice(0, 2)].filter(Boolean).join(" · ")}</span>
              <h1 id="taste-lab-movie-title" ref={activeTitleRef} tabIndex={-1}>{activeCandidate.movie.title}</h1>
              <p>How did this movie land for you?</p>
            </div>
          </article>

          <section className={styles.choices} aria-label={`Your opinion of ${activeCandidate.movie.title}`}>
            <div className={styles.preferenceChoices} role="group" aria-label="Taste preference">
              {tasteLabChoiceGroups.preference.map((choice) => (
                <button
                  key={choice.value}
                  type="button"
                  aria-pressed={selectedLabel === choice.value}
                  onClick={() => choose(choice.value)}
                  disabled={busy}
                >
                  <WatchSignalIcon name={choice.icon} />
                  <span>{choice.label}</span>
                </button>
              ))}
            </div>
            <div className={styles.familiarity}>
              <span><strong>Haven’t seen it?</strong><small>This records familiarity only.</small></span>
              <button
                type="button"
                aria-pressed={selectedLabel === tasteLabChoiceGroups.familiarity.value}
                onClick={() => choose(tasteLabChoiceGroups.familiarity.value)}
                disabled={busy}
              >
                <WatchSignalIcon name="eye-off" />
                {tasteLabChoiceGroups.familiarity.label}
              </button>
            </div>
          </section>

          <section className={styles.actionArea}>
            <p className={queueState === "error" ? styles.error : undefined} role={queueState === "error" ? "alert" : "status"} aria-live="polite">
              {status}
            </p>
            {queueState === "error" ? (
              <div className={styles.recoveryActions}>
                <button type="button" onClick={keepCurrentChoiceLocally}>Keep on this phone</button>
                <button className={styles.primary} type="button" onClick={() => void saveAndNext()}>Try again</button>
              </div>
            ) : (
              <button className={styles.primary} type="button" onClick={() => void saveAndNext()} disabled={!selectedLabel || busy}>
                {busy ? "Saving…" : isLocal ? "Keep & next" : "Save & next"}
                {!busy ? <WatchSignalIcon name="chevron-right" /> : null}
              </button>
            )}
          </section>
        </>
      ) : (
        <TasteLabState
          state={queueState}
          status={status}
          busy={busy}
          onAction={queueState === "empty" ? seedQueue : () => refresh(profileId)}
        />
      )}

      <details className={styles.summary}>
        <summary>Your Taste Lab progress</summary>
        <div>
          <span><strong>{history.length}</strong> answered</span>
          <span><strong>{importableCount}</strong> taste choices</span>
          <span><strong>{familiarityCount}</strong> not seen</span>
          <span><strong>{coverage}</strong> genres</span>
        </div>
        <p>{isLocal ? "Using built-in movies on this phone." : "Saved privately to this household profile."}</p>
      </details>
    </main>
  );
}

function TasteLabState({ state, status, busy, onAction }: {
  state: TasteLabQueueState;
  status: string;
  busy: boolean;
  onAction: () => void | Promise<void>;
}) {
  const loading = state === "loading";
  const localExhausted = state === "local-exhausted";
  const empty = state === "empty";
  const batchComplete = state === "batch-complete";
  return (
    <section className={styles.state} aria-live="polite">
      <span className={styles.stateIcon}><WatchSignalIcon name={loading ? "refresh" : localExhausted ? "eye-off" : empty ? "sparkles" : "check"} /></span>
      <small>{loading ? "Taste Lab" : localExhausted ? "Offline" : batchComplete ? "Batch complete" : empty ? "Ready when you are" : "All caught up"}</small>
      <h1>{loading ? "Finding useful movies…" : localExhausted ? "No built-in movies left" : batchComplete ? "Nice work" : empty ? "Start with a few movies" : "You’ve answered them all"}</h1>
      <p>{status}</p>
      {!loading ? (
        <button type="button" onClick={() => void onAction()} disabled={busy || localExhausted}>
          {busy ? "Checking…" : empty ? "Start Taste Lab" : batchComplete ? "Check next batch" : localExhausted ? "Reconnect to continue" : "Check for more"}
        </button>
      ) : <div className={styles.loadingBars} aria-hidden="true"><i /><i /><i /></div>}
    </section>
  );
}

function ratingInput(
  candidate: TasteLabCandidatePayload,
  label: TasteLabRatingLabel,
): TasteLabRatingInputPayload {
  return {
    movie: candidate.movie,
    label,
    queueProvenance: candidate.queueProvenance,
    ratedAt: new Date().toISOString(),
  };
}

function profileLabel(profileId: string, profiles: SetupProfilePayload[]): string {
  return profiles.find((profile) => profile.id === profileId)?.label
    ?? fallbackProfiles.find((profile) => profile.id === profileId)?.label
    ?? "Profile";
}

function posterUrl(path: string): string {
  return path.startsWith("http") ? path : `https://image.tmdb.org/t/p/w500${path}`;
}

function localDemoQueue(savedRatings: TasteLabRatingExportPayload[]): TasteLabCandidatePayload[] {
  const ratedMovieIds = new Set(savedRatings.map((rating) => rating.movie.sourceMovieId));
  return demoTasteLabCandidates.filter((candidate) => !ratedMovieIds.has(candidate.movie.sourceMovieId));
}

function localRatingExport(
  household: string,
  profile: string,
  rating: TasteLabRatingInputPayload,
  ratedAt: string,
): TasteLabRatingExportPayload {
  const preferenceValueByLabel: Record<TasteLabRatingLabel, number | null> = {
    loved: 1,
    liked: 0.65,
    meh: 0,
    hated: -1,
    havent_seen: null,
  };
  const isImportablePreference = rating.label !== "havent_seen";
  return {
    schemaVersion: "taste_lab.rating_export.v1",
    householdId: household,
    profileId: profile,
    movie: rating.movie,
    label: rating.label,
    familiarity: isImportablePreference ? "seen" : "unseen",
    preferenceValue: preferenceValueByLabel[rating.label],
    watchsignalTasteSignal: isImportablePreference ? rating.label : "familiarity_only",
    isImportablePreference,
    ratedAt,
    queueProvenance: rating.queueProvenance ?? null,
  };
}

const demoTasteLabCandidates: TasteLabCandidatePayload[] = [
  demoCandidate(1, "movielens:1", "Arrival", 2016, "/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg", ["Sci-Fi", "Drama", "Mystery"]),
  demoCandidate(2, "movielens:2", "Knives Out", 2019, "/pThyQovXQrw2m0s9x82twj48Jq4.jpg", ["Mystery", "Comedy", "Crime"]),
  demoCandidate(3, "movielens:3", "The Matrix", 1999, "/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg", ["Action", "Sci-Fi"]),
  demoCandidate(4, "movielens:4", "Parasite", 2019, "/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg", ["Thriller", "Drama", "Comedy"]),
  demoCandidate(5, "movielens:5", "Mad Max: Fury Road", 2015, "/hA2ple9q4qnwxp3hKVNhroipsir.jpg", ["Action", "Adventure", "Sci-Fi"]),
  demoCandidate(6, "movielens:6", "Eternal Sunshine of the Spotless Mind", 2004, "/5MwkWH9tYHv3mV9OdYTMR5qreIz.jpg", ["Romance", "Drama", "Sci-Fi"]),
  demoCandidate(7, "movielens:7", "Spirited Away", 2001, "/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg", ["Animation", "Fantasy", "Adventure"]),
  demoCandidate(8, "movielens:8", "The Grand Budapest Hotel", 2014, "/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg", ["Comedy", "Adventure", "Crime"]),
  demoCandidate(9, "movielens:9", "Edge of Tomorrow", 2014, "/xjw5trHV7Mwo61P0kCTy8paEkgO.jpg", ["Action", "Sci-Fi", "Adventure"]),
  demoCandidate(10, "movielens:10", "Past Lives", 2023, "/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg", ["Romance", "Drama"]),
];

function demoCandidate(
  rank: number,
  sourceMovieId: string,
  title: string,
  releaseYear: number,
  posterPath: string,
  genres: string[],
): TasteLabCandidatePayload {
  return {
    movie: { sourceMovieId, title, releaseYear, posterPath, genres },
    queueProvenance: {
      queueSource: "offline_demo",
      rank,
      signalScore: null,
      scoreComponents: {},
      queueReason: "Built-in taste check",
    },
  };
}
