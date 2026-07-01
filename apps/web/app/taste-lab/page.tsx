"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getTasteLabQueue,
  getTasteLabRatings,
  seedTasteLabCandidates,
  submitTasteLabRatings,
  type TasteLabCandidatePayload,
  type TasteLabRatingExportPayload,
  type TasteLabRatingInputPayload,
  type TasteLabRatingLabel,
} from "../taste-lab-client";

const householdId = "default-household";
const profiles = [
  { id: "sandy", label: "Sandy" },
  { id: "robin", label: "Robin" },
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
  { value: "havent_seen", label: "Haven't seen", cue: "skip for now" },
];

export default function TasteLabPage() {
  const [profileId, setProfileId] = useState(profiles[0].id);
  const [queue, setQueue] = useState<TasteLabCandidatePayload[]>([]);
  const [ratings, setRatings] = useState<Record<string, TasteLabRatingLabel>>({});
  const [history, setHistory] = useState<TasteLabRatingExportPayload[]>([]);
  const [status, setStatus] = useState("Loading Taste Lab.");
  const [busy, setBusy] = useState(false);

  const selectedCount = Object.keys(ratings).length;
  const importableCount = history.filter((rating) => rating.isImportablePreference).length;
  const unseenCount = history.length - importableCount;
  const activeProfile = profiles.find((profile) => profile.id === profileId) ?? profiles[0];

  useEffect(() => {
    void refresh(profileId);
  }, [profileId]);

  async function refresh(nextProfileId = profileId) {
    setBusy(true);
    setStatus("Refreshing the queue.");
    try {
      const [nextQueue, savedRatings] = await Promise.all([
        getTasteLabQueue(householdId, nextProfileId, 10),
        getTasteLabRatings(householdId, nextProfileId),
      ]);
      setQueue(nextQueue);
      setHistory(savedRatings);
      setRatings({});
      setStatus(
        nextQueue.length > 0
          ? "Queue ready."
          : "No candidates yet. Seed the demo queue to start.",
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Taste Lab could not load.");
    } finally {
      setBusy(false);
    }
  }

  async function seedDemoQueue() {
    setBusy(true);
    setStatus("Seeding demo candidates.");
    try {
      await seedTasteLabCandidates(householdId, demoTasteLabCandidates);
      await refresh(profileId);
      setStatus("Demo queue seeded.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Demo queue could not be seeded.");
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
      await refresh(profileId);
      setStatus(`${selectedRatings.length} signal${selectedRatings.length === 1 ? "" : "s"} saved.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Ratings could not be saved.");
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
          <button type="button" onClick={seedDemoQueue} disabled={busy}>
            Seed demo queue
          </button>
          <button type="button" onClick={() => refresh(profileId)} disabled={busy}>
            Refresh
          </button>
        </div>
      </section>

      <section className="tasteLabQueueHeader">
        <div>
          <p className="eyebrow">{activeProfile.label}'s batch</p>
          <h2>{selectedCount} of {queue.length} selected</h2>
        </div>
        <button type="button" onClick={submitBatch} disabled={busy || selectedCount === 0}>
          Save batch
        </button>
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
    </main>
  );
}

function posterUrl(path: string): string {
  if (path.startsWith("http") || path.startsWith("/")) {
    return path;
  }

  return `https://image.tmdb.org/t/p/w342${path}`;
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
