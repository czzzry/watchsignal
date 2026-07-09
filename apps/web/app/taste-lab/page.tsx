"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ensureTesterProfile,
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

const householdId = "default-household";
const testerProfileId = "cezary-tester";
const fallbackProfiles: SetupProfilePayload[] = [
  {
    id: testerProfileId,
    label: "Cezary - tester",
    order: 1,
    avatarKey: "comet",
    colorKey: "amber",
  },
  {
    id: "profile-1",
    label: "Husband",
    order: 2,
    avatarKey: "spark",
    colorKey: "cyan",
  },
  {
    id: "profile-2",
    label: "Wife",
    order: 3,
    avatarKey: "moon",
    colorKey: "rose",
  },
];

const labels: {
  value: TasteLabRatingLabel;
  label: string;
  cue: string;
}[] = [
  { value: "loved", label: "Loved", cue: "strong yes" },
  { value: "liked", label: "Liked", cue: "good fit" },
  { value: "meh", label: "Meh", cue: "neutral" },
  { value: "hated", label: "Hated", cue: "strong no" },
  { value: "havent_seen", label: "Haven't seen", cue: "not a taste vote" },
];

export default function TasteLabPage() {
  const [profiles, setProfiles] = useState<SetupProfilePayload[]>(fallbackProfiles);
  const [profileId, setProfileId] = useState(testerProfileId);
  const [queue, setQueue] = useState<TasteLabCandidatePayload[]>([]);
  const [ratings, setRatings] = useState<Record<string, TasteLabRatingLabel>>({});
  const [history, setHistory] = useState<TasteLabRatingExportPayload[]>([]);
  const [status, setStatus] = useState("Loading Taste Lab.");
  const [busy, setBusy] = useState(false);

  const selectedCount = Object.keys(ratings).length;
  const importableCount = history.filter((rating) => rating.isImportablePreference).length;
  const unseenCount = history.length - importableCount;
  const activeProfile = profiles.find((profile) => profile.id === profileId) ?? profiles[0];
  const queueSource = queue[0]?.queueProvenance.queueSource ?? null;
  const queueSourceLabel = queueSourceLabelFor(queueSource);
  const queueSourceDetail = queueSourceDetailFor(queueSource);

  useEffect(() => {
    void loadProfiles();
  }, []);

  useEffect(() => {
    void refresh(profileId);
  }, [profileId]);

  async function loadProfiles() {
    try {
      const setup = await ensureTesterProfile();
      const sortedProfiles = [...setup.profiles].sort(
        (first, second) => first.order - second.order,
      );
      setProfiles(sortedProfiles);
      setProfileId((currentProfileId) =>
        sortedProfiles.some((profile) => profile.id === currentProfileId)
          ? currentProfileId
          : sortedProfiles.some((profile) => profile.id === testerProfileId)
            ? testerProfileId
            : sortedProfiles[0]?.id ?? testerProfileId,
      );
    } catch {
      setProfiles(fallbackProfiles);
      setProfileId(testerProfileId);
    }
  }

  async function refresh(nextProfileId = profileId) {
    setBusy(true);
    setStatus("Refreshing the queue.");
    try {
      const { nextQueue, savedRatings } = await loadProfileState(nextProfileId);
      setStatus(
        nextQueue.length > 0
          ? "Queue ready."
          : savedRatings.length > 0
            ? `No unrated queued movies remain for ${profileLabel(nextProfileId, profiles)}.`
          : "No candidates yet. Load the high-signal queue to start.",
      );
    } catch (error) {
      const nextQueue = localDemoQueue(history);
      setQueue(nextQueue);
      setRatings({});
      setStatus(
        nextQueue.length > 0
          ? "API offline. Showing the remaining local demo queue."
          : "API offline. No local demo candidates remain for this profile.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function loadProfileState(nextProfileId = profileId): Promise<{
    nextQueue: TasteLabCandidatePayload[];
    savedRatings: TasteLabRatingExportPayload[];
  }> {
    const [nextQueue, savedRatings] = await Promise.all([
      getTasteLabQueue(householdId, nextProfileId, 10),
      getTasteLabRatings(householdId, nextProfileId),
    ]);

    setQueue(nextQueue);
    setHistory(savedRatings);
    setRatings({});

    return { nextQueue, savedRatings };
  }

  async function seedSmartQueue() {
    setBusy(true);
    setStatus("Loading the high-signal queue.");
    try {
      await seedDefaultTasteLabCandidates(householdId);
      const { nextQueue, savedRatings } = await loadProfileState(profileId);
      setStatus(
        nextQueue.length > 0
          ? "High-signal queue loaded. Rate this batch, then confirm at the bottom."
          : savedRatings.length > 0
            ? `All high-signal starter movies are already answered for ${profileLabel(profileId, profiles)}. Switch profiles or reset the test data to start over.`
            : "High-signal queue loaded, but no batch came back.",
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "High-signal queue could not be loaded.";
      if (message.includes("Taste Lab seed queue artifact is missing")) {
        setQueue([]);
        setRatings({});
        setStatus(message);
        return;
      }

      const nextQueue = demoTasteLabCandidates;
      setQueue(nextQueue);
      setRatings({});
      setStatus(
        nextQueue.length > 0
          ? "API offline. Loaded the small local fallback queue. Ratings will stay in this browser until the API reconnects."
          : "API offline. No local demo candidates are available.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function submitBatch() {
    const selectedRatings: TasteLabRatingInputPayload[] = queue
      .filter((candidate) => ratings[candidate.movie.sourceMovieId])
      .map((candidate) => ({
        movie: candidate.movie,
        label: ratings[candidate.movie.sourceMovieId],
        queueProvenance: candidate.queueProvenance,
        ratedAt: new Date().toISOString(),
      }));

    if (selectedRatings.length === 0) {
      setStatus("Pick at least one label before saving.");
      return;
    }

    setBusy(true);
    setStatus("Saving taste signals.");
    try {
      await submitTasteLabRatings(householdId, profileId, selectedRatings);
      const { nextQueue } = await loadProfileState(profileId);
      setStatus(
        nextQueue.length > 0
          ? `${selectedRatings.length} signal${selectedRatings.length === 1 ? "" : "s"} saved. Next batch is ready.`
          : `${selectedRatings.length} signal${selectedRatings.length === 1 ? "" : "s"} saved. No unrated queued movies remain for ${profileLabel(profileId, profiles)}.`,
      );
    } catch (error) {
      const savedAt = new Date().toISOString();
      const localRatings = selectedRatings.map((rating) =>
        localRatingExport(householdId, profileId, rating, savedAt),
      );
      const ratedMovieIds = new Set(
        selectedRatings.map((rating) => rating.movie.sourceMovieId),
      );

      setHistory((current) => [...localRatings, ...current]);
      setQueue((current) =>
        current.filter((candidate) => !ratedMovieIds.has(candidate.movie.sourceMovieId)),
      );
      setRatings({});
      setStatus(
        `${selectedRatings.length} local signal${selectedRatings.length === 1 ? "" : "s"} captured. API is offline, so this is not permanently saved yet.`,
      );
    } finally {
      setBusy(false);
    }
  }

  const coverage = useMemo(() => {
    const genres = new Set<string>();
    history.forEach((rating) => {
      rating.movie.genres.forEach((genre) => genres.add(genre));
    });
    return genres.size;
  }, [history]);

  return (
    <main className="tasteLabShell">
      <section className="tasteLabHeader">
        <p className="eyebrow">Private Taste Lab</p>
        <h1>Build a sharper taste profile.</h1>
        <p>
          Rate high-signal movies in quick batches.
          WatchSignal saves preference separately from familiarity.
        </p>
      </section>

      <section className="syncStrip" aria-label="Taste Lab queue source" role="status">
        <div>
          <span>{queueSourceLabel}</span>
          <p>{queueSourceDetail}</p>
        </div>
      </section>

      <section className="tasteLabControlPanel" aria-label="Taste Lab controls">
        <div className="tasteLabProfileTabs" role="tablist" aria-label="Profile">
          {profiles.map((profile) => (
            <button
              key={profile.id}
              type="button"
              className={profile.id === profileId ? "isActive" : ""}
              onClick={() => setProfileId(profile.id)}
            >
              {profile.label}
            </button>
          ))}
        </div>

        <div className="tasteLabStats" aria-label="Taste Lab progress">
          <span>
            <strong>{history.length}</strong>
            rated
          </span>
          <span>
            <strong>{importableCount}</strong>
            taste signals
          </span>
          <span>
            <strong>{unseenCount}</strong>
            unseen
          </span>
          <span>
            <strong>{coverage}</strong>
            genres
          </span>
        </div>

        <div className="tasteLabActions">
          <button type="button" onClick={seedSmartQueue} disabled={busy}>
            Load high-signal queue
          </button>
          <button type="button" onClick={() => refresh(profileId)} disabled={busy}>
            Check next batch
          </button>
        </div>
      </section>

      <section className="tasteLabQueueHeader">
        <div>
          <p className="eyebrow">{activeProfile.label}'s batch</p>
          <h2>{selectedCount} of {queue.length} selected</h2>
        </div>
      </section>

      <section className="tasteLabStatus" aria-live="polite">
        {status}
      </section>

      <section className="tasteLabGrid" aria-label="Taste Lab movie queue">
        {queue.map((candidate) => (
          <article className="tasteLabCard" key={candidate.movie.sourceMovieId}>
            <div className="tasteLabPoster">
              {candidate.movie.posterPath ? (
                <img src={posterUrl(candidate.movie.posterPath)} alt="" />
              ) : (
                <span>{candidate.movie.title}</span>
              )}
            </div>
            <div className="tasteLabCardBody">
              <div className="tasteLabMovieTitle">
                <h3>{candidate.movie.title}</h3>
                <span>{candidate.movie.releaseYear}</span>
              </div>
              <p>
                Signal {percent(candidate.queueProvenance.signalScore)}
                {" "}• Rank {candidate.queueProvenance.rank ?? "new"}
              </p>
              <div className="tasteLabGenreRow">
                {candidate.movie.genres.slice(0, 3).map((genre) => (
                  <span key={genre}>{genre}</span>
                ))}
              </div>
              <div className="tasteLabLabelGrid" aria-label={`Rate ${candidate.movie.title}`}>
                {labels.map((label) => {
                  const selected = ratings[candidate.movie.sourceMovieId] === label.value;
                  return (
                    <button
                      key={label.value}
                      type="button"
                      className={selected ? "isSelected" : ""}
                      onClick={() =>
                        setRatings((current) => ({
                          ...current,
                          [candidate.movie.sourceMovieId]: label.value,
                        }))
                      }
                    >
                      <strong>{label.label}</strong>
                      <span>{label.cue}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </article>
        ))}
      </section>

      <section className="tasteLabBatchFooter" aria-label="Taste Lab batch actions">
        {queue.length > 0 ? (
          <>
            <button type="button" onClick={submitBatch} disabled={busy || selectedCount === 0}>
              Confirm ratings
            </button>
            <p>
              {selectedCount === 0
                ? "Select a reaction for at least one movie, then confirm."
                : `${selectedCount} selected for ${activeProfile.label}.`}
            </p>
          </>
        ) : (
          <>
            <button type="button" onClick={seedSmartQueue} disabled={busy}>
              Load high-signal queue
            </button>
            <p>
              Use this to start calibration or check whether any unrated starter movies remain.
            </p>
          </>
        )}
      </section>
    </main>
  );
}

function queueSourceLabelFor(queueSource: string | null): string {
  if (queueSource === null) {
    return "Queue source pending";
  }

  if (queueSource.startsWith("movielens_signal_score_v1")) {
    return "Stored signal queue";
  }

  if (queueSource.includes("demo") || queueSource.includes("offline")) {
    return "Local demo queue";
  }

  return "Saved queue";
}

function queueSourceDetailFor(queueSource: string | null): string {
  if (queueSource === null) {
    return "Taste Lab is loading the current queue source.";
  }

  if (queueSource.startsWith("movielens_signal_score_v1")) {
    return "Taste Lab is using the stored high-signal MovieLens queue from the backend, not live TMDb discovery.";
  }

  if (queueSource.includes("demo") || queueSource.includes("offline")) {
    return "Taste Lab is showing the local demo fallback queue.";
  }

  return `Taste Lab queue source: ${queueSource}.`;
}

function profileLabel(
  profileId: string,
  profiles: SetupProfilePayload[] = fallbackProfiles,
): string {
  return (
    profiles.find((profile) => profile.id === profileId)?.label
    ?? fallbackProfiles.find((profile) => profile.id === profileId)?.label
    ?? profileId
  );
}

function posterUrl(path: string): string {
  if (path.startsWith("http")) {
    return path;
  }

  return `https://image.tmdb.org/t/p/w342${path}`;
}

function localDemoQueue(
  savedRatings: TasteLabRatingExportPayload[],
): TasteLabCandidatePayload[] {
  const ratedMovieIds = new Set(
    savedRatings.map((rating) => rating.movie.sourceMovieId),
  );

  return demoTasteLabCandidates.filter(
    (candidate) => !ratedMovieIds.has(candidate.movie.sourceMovieId),
  );
}

function localRatingExport(
  householdId: string,
  profileId: string,
  rating: TasteLabRatingInputPayload,
  ratedAt: string,
): TasteLabRatingExportPayload {
  const preferenceValueByLabel: Record<TasteLabRatingLabel, number | null> = {
    loved: 2,
    liked: 1,
    meh: 0,
    hated: -2,
    havent_seen: null,
  };
  const isImportablePreference = rating.label !== "havent_seen";

  return {
    schemaVersion: "taste_lab.rating_export.v1",
    householdId,
    profileId,
    movie: rating.movie,
    label: rating.label,
    familiarity: isImportablePreference ? "seen" : "unseen",
    preferenceValue: preferenceValueByLabel[rating.label],
    watchsignalTasteSignal: isImportablePreference
      ? `Local Taste Lab demo: ${rating.label}`
      : "Local Taste Lab demo: not seen",
    isImportablePreference,
    ratedAt,
    queueProvenance: rating.queueProvenance ?? null,
  };
}

function percent(value: number | null | undefined): string {
  if (typeof value !== "number") {
    return "pending";
  }

  return `${Math.round(value * 100)}%`;
}

const demoTasteLabCandidates: TasteLabCandidatePayload[] = [
  demoCandidate(1, "movielens:1", "Arrival", 2016, "tt2543164", "/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg", ["Sci-Fi", "Drama", "Mystery"], 0.94),
  demoCandidate(2, "movielens:2", "Knives Out", 2019, "tt8946378", "/pThyQovXQrw2m0s9x82twj48Jq4.jpg", ["Mystery", "Comedy", "Crime"], 0.91),
  demoCandidate(3, "movielens:3", "The Matrix", 1999, "tt0133093", "/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg", ["Action", "Sci-Fi"], 0.89),
  demoCandidate(4, "movielens:4", "Parasite", 2019, "tt6751668", "/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg", ["Thriller", "Drama", "Comedy"], 0.88),
  demoCandidate(5, "movielens:5", "Mad Max: Fury Road", 2015, "tt1392190", "/hA2ple9q4qnwxp3hKVNhroipsir.jpg", ["Action", "Adventure", "Sci-Fi"], 0.86),
  demoCandidate(6, "movielens:6", "Eternal Sunshine of the Spotless Mind", 2004, "tt0338013", "/5MwkWH9tYHv3mV9OdYTMR5qreIz.jpg", ["Romance", "Drama", "Sci-Fi"], 0.84),
  demoCandidate(7, "movielens:7", "Spirited Away", 2001, "tt0245429", "/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg", ["Animation", "Fantasy", "Adventure"], 0.82),
  demoCandidate(8, "movielens:8", "The Grand Budapest Hotel", 2014, "tt2278388", "/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg", ["Comedy", "Adventure", "Crime"], 0.8),
  demoCandidate(9, "movielens:9", "Edge of Tomorrow", 2014, "tt1631867", "/xjw5trHV7Mwo61P0kCTy8paEkgO.jpg", ["Action", "Sci-Fi", "Adventure"], 0.78),
  demoCandidate(10, "movielens:10", "Past Lives", 2023, "tt13238346", "/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg", ["Romance", "Drama"], 0.76),
];

function demoCandidate(
  rank: number,
  sourceMovieId: string,
  title: string,
  releaseYear: number,
  tmdbId: string,
  posterPath: string,
  genres: string[],
  signalScore: number,
): TasteLabCandidatePayload {
  return {
    movie: {
      sourceMovieId,
      title,
      releaseYear,
      tmdbId,
      posterPath,
      genres,
    },
    queueProvenance: {
      queueSource: "offline_signal_score_v1_demo",
      generatedAt: "2026-07-01T12:00:00Z",
      rank,
      signalScore,
      scoreComponents: {
        recognizability: Math.max(0.6, signalScore - 0.02),
        divisiveness: Math.max(0.55, signalScore - 0.08),
        coverage: Math.max(0.5, signalScore - 0.12),
        non_redundancy: Math.max(0.45, signalScore - 0.18),
      },
    },
  };
}
