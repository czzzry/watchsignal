"use client";

import { useState } from "react";
import styles from "./golden-result.module.css";

type CastMember = {
  name: string;
  character: string;
  profile: string;
};

type GoldenMovie = {
  id: number;
  title: string;
  year: number;
  runtime: string;
  genres: string;
  score: number;
  poster: string;
  backdrop: string;
  overview: string;
  cast: CastMember[];
  reason: string;
  reactions: string;
  watchLabel: string;
  watchDetail: string;
  evidence: string[];
};

const movies: GoldenMovie[] = [
  {
    id: 329865,
    title: "Arrival",
    year: 2016,
    runtime: "1h 56m",
    genres: "Drama · Sci-Fi · Mystery",
    score: 84,
    poster: "https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
    backdrop: "https://image.tmdb.org/t/p/original/hNCqkXbWd40eftqSdjq8TmV7Mqr.jpg",
    overview: "After alien crafts land around the world, an expert linguist is recruited by the military to determine whether the visitors come in peace or pose a threat.",
    cast: [
      { name: "Amy Adams", character: "Louise Banks", profile: "https://image.tmdb.org/t/p/w185/1h2r2VTpoFb5QefAaBYYQgQzL9z.jpg" },
      { name: "Jeremy Renner", character: "Ian Donnelly", profile: "https://image.tmdb.org/t/p/w185/yB84D1neTYXfWBaV0QOE9RF2VCu.jpg" },
      { name: "Forest Whitaker", character: "Colonel Weber", profile: "https://image.tmdb.org/t/p/w185/4w7l5JUwnwFNBy7J93ZwYN1nihm.jpg" },
    ],
    reason: "Thoughtful and tense, without going bleak.",
    reactions: "Both interested",
    watchLabel: "Amazon Video",
    watchDetail: "Rent or buy in Germany",
    evidence: ["Both interested", "Strong mood fit", "Under two hours"],
  },
  {
    id: 546554,
    title: "Knives Out",
    year: 2019,
    runtime: "2h 11m",
    genres: "Comedy · Crime · Mystery",
    score: 72,
    poster: "https://image.tmdb.org/t/p/w500/pThyQovXQrw2m0s9x82twj48Jq4.jpg",
    backdrop: "https://image.tmdb.org/t/p/original/4HWAQu28e2yaWrtupFPGFkdNU7V.jpg",
    overview: "Detective Benoit Blanc investigates the death of a celebrated crime novelist and finds every member of the wildly dysfunctional family hiding something.",
    cast: [
      { name: "Daniel Craig", character: "Benoit Blanc", profile: "https://image.tmdb.org/t/p/w185/iFerDZUmC5Fu26i4qI8xnUVEHc7.jpg" },
      { name: "Ana de Armas", character: "Marta Cabrera", profile: "https://image.tmdb.org/t/p/w185/eDuBeSHV0R7vuCnHHXrfa7d7IfB.jpg" },
      { name: "Chris Evans", character: "Ransom Drysdale", profile: "https://image.tmdb.org/t/p/w185/3bOGNsHlrswhyW79uvIHH1V43JI.jpg" },
    ],
    reason: "Lighter and faster, with a strong shared reaction.",
    reactions: "Interested + maybe",
    watchLabel: "Netflix",
    watchDetail: "Included in Germany",
    evidence: ["Strong shared fit", "Clever and funny", "Longer than requested"],
  },
  {
    id: 666277,
    title: "Past Lives",
    year: 2023,
    runtime: "1h 46m",
    genres: "Drama · Romance",
    score: 61,
    poster: "https://image.tmdb.org/t/p/w500/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg",
    backdrop: "https://image.tmdb.org/t/p/original/7HR38hMBl23lf38MAN63y4pKsHz.jpg",
    overview: "Childhood friends Nora and Hae Sung reunite in New York for one fateful weekend and confront destiny, love, and the choices that make a life.",
    cast: [
      { name: "Greta Lee", character: "Nora", profile: "https://image.tmdb.org/t/p/w185/6SydTis4XUcovlwIGskT59JowLX.jpg" },
      { name: "Teo Yoo", character: "Hae Sung", profile: "https://image.tmdb.org/t/p/w185/vuzKCKo2kIskjbDEcl2EMLv6uhO.jpg" },
      { name: "John Magaro", character: "Arthur", profile: "https://image.tmdb.org/t/p/w185/ah4Jm4Lmrgab9xdHwRId80S4REd.jpg" },
    ],
    reason: "Emotionally precise, but quieter than tonight’s mood.",
    reactions: "Maybe + interested",
    watchLabel: "WOW",
    watchDetail: "Included in Germany",
    evidence: ["Both open to it", "Excellent runtime", "Quieter than requested"],
  },
  {
    id: 120467,
    title: "The Grand Budapest Hotel",
    year: 2014,
    runtime: "1h 40m",
    genres: "Comedy · Drama",
    score: 52,
    poster: "https://image.tmdb.org/t/p/w500/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg",
    backdrop: "https://image.tmdb.org/t/p/original/9udCLTxTFl28RxnK8Q05E154ZGa.jpg",
    overview: "A legendary concierge and his trusted lobby boy become entangled in the theft of a priceless painting and a battle over an enormous family fortune.",
    cast: [
      { name: "Ralph Fiennes", character: "M. Gustave", profile: "https://image.tmdb.org/t/p/w185/tJr9GcmGNHhLVVEH3i7QYbj6hBi.jpg" },
      { name: "F. Murray Abraham", character: "Mr. Moustafa", profile: "https://image.tmdb.org/t/p/w185/p2RYVGdrcP0m70BkkiKcwyrDeim.jpg" },
      { name: "Mathieu Amalric", character: "Serge X.", profile: "https://image.tmdb.org/t/p/w185/fMhfoTbjlXQy2Iojp7oYx49hLQl.jpg" },
    ],
    reason: "Playful and beautiful, with a weaker shared signal.",
    reactions: "Both maybe",
    watchLabel: "Prime Video",
    watchDetail: "Included in Germany",
    evidence: ["Playful tone", "Shortest option", "Weaker shared reaction"],
  },
  {
    id: 137113,
    title: "Edge of Tomorrow",
    year: 2014,
    runtime: "1h 54m",
    genres: "Action · Sci-Fi",
    score: 38,
    poster: "https://image.tmdb.org/t/p/w500/nBM9MMa2WCwvMG4IJ3eiGUdbPe6.jpg",
    backdrop: "https://image.tmdb.org/t/p/original/4V1yIoAKPMRQwGBaSses8Bp2nsi.jpg",
    overview: "An inexperienced officer is killed in combat and wakes at the beginning of the same day, forced to fight the alien invasion again and again.",
    cast: [
      { name: "Tom Cruise", character: "Cage", profile: "https://image.tmdb.org/t/p/w185/maf8PhSvDCdEwjEMbYfGpojR5RP.jpg" },
      { name: "Emily Blunt", character: "Rita", profile: "https://image.tmdb.org/t/p/w185/5nCSG5TL1bP1geD8aaBfaLnLLCD.jpg" },
      { name: "Brendan Gleeson", character: "General Brigham", profile: "https://image.tmdb.org/t/p/w185/ctPPJu5ZYDZr1IPmzoNpezczrm0.jpg" },
    ],
    reason: "Strong pace, but one clear no pulls it down.",
    reactions: "Interested + no",
    watchLabel: "Amazon Video",
    watchDetail: "Rent or buy in Germany",
    evidence: ["Strong pace", "Good runtime", "One clear no"],
  },
];

export function GoldenResult({ onFiveMore }: { onFiveMore: () => void }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [watchReady, setWatchReady] = useState(false);
  const movie = movies[activeIndex];
  const rank = activeIndex + 1;
  const nextScore = movies[Math.min(activeIndex + 1, movies.length - 1)].score;

  function selectMovie(index: number) {
    setActiveIndex(index);
    setDetailsOpen(false);
    setWatchReady(false);
  }

  return (
    <section className={styles.resultScreen} aria-label="Golden result reference">
      <img key={movie.backdrop} className={styles.backdrop} src={movie.backdrop} alt="" />
      <div className={styles.colorWash} />
      <div className={styles.backdropShade} />

      <header className={styles.header}>
        <div className={styles.brand}><span>W</span><strong>WatchSignal</strong></div>
        <div className={styles.position}><i>{rank}</i><span>of 5</span></div>
      </header>

      <div className={styles.resultBody}>
        <div className={styles.signalRow}>
          <ScoreDial score={movie.score} />
          <div>
            <strong>{rank === 1 ? "Tonight’s strongest match" : `Ranked #${rank} tonight`}</strong>
            <span>{rank === 1 ? `${movie.score - nextScore} points clear` : movie.reactions}</span>
          </div>
        </div>

        <button className={styles.titleBlock} type="button" onClick={() => setDetailsOpen(true)} aria-label={`Open details for ${movie.title}`}>
          <h1>{movie.title}</h1>
          <p>{movie.year} · {movie.runtime} · {movie.genres}</p>
          <span><b>{movie.reactions}</b> {movie.reason}</span>
        </button>

        <div className={styles.filmstrip} aria-label="Ranked alternatives">
          {movies.map((item, index) => (
            <button key={item.id} className={index === activeIndex ? styles.filmActive : ""} type="button" onClick={() => selectMovie(index)} aria-label={`${index + 1}. ${item.title}, score ${item.score}`}>
              <img src={item.poster} alt="" />
              <span>{item.score}</span>
            </button>
          ))}
        </div>

        <div className={styles.actionDock} role="group" aria-label="Result actions">
          <button type="button" onClick={() => setDetailsOpen(true)}><InfoIcon /><span>Details</span></button>
          <button className={styles.watchAction} type="button" onClick={() => setWatchReady(true)}><PlayIcon /><span>Watch</span></button>
          <button type="button" onClick={onFiveMore}><RefreshIcon /><span>5 more</span></button>
        </div>
      </div>

      {watchReady ? (
        <div className={styles.watchToast} role="status">
          <span><PlayIcon /></span>
          <div><strong>{movie.watchLabel}</strong><small>{movie.watchDetail}</small></div>
          <button type="button" onClick={() => setWatchReady(false)}>Close</button>
        </div>
      ) : null}

      {detailsOpen ? <DetailsSheet movie={movie} onClose={() => setDetailsOpen(false)} onWatch={() => setWatchReady(true)} /> : null}
    </section>
  );
}

function DetailsSheet({ movie, onClose, onWatch }: { movie: GoldenMovie; onClose: () => void; onWatch: () => void }) {
  return (
    <div className={styles.detailsLayer}>
      <button className={styles.detailsBackdrop} type="button" aria-label="Close details" onClick={onClose} />
      <section className={styles.detailsSheet} role="dialog" aria-modal="true" aria-label={`${movie.title} details`}>
        <span className={styles.sheetHandle} aria-hidden="true" />
        <header className={styles.sheetHeader}>
          <img src={movie.poster} alt="" />
          <div><span>{movie.year} · {movie.runtime}</span><h2>{movie.title}</h2><p>{movie.genres}</p></div>
          <button type="button" onClick={onClose} aria-label="Close details"><CloseIcon /></button>
        </header>

        <div className={styles.sheetScroll}>
          <section className={styles.synopsis}>
            <h3>What it’s about</h3>
            <p>{movie.overview}</p>
          </section>

          <section className={styles.castSection}>
            <h3>Who’s in it</h3>
            <div className={styles.castList}>
              {movie.cast.map((person) => (
                <article key={person.name}>
                  <img src={person.profile} alt="" />
                  <strong>{person.name}</strong>
                  <span>{person.character}</span>
                </article>
              ))}
            </div>
          </section>

          <section className={styles.whySection}>
            <div><h3>Why {movie.score}</h3><span>{movie.reactions}</span></div>
            <ul>{movie.evidence.map((item) => <li key={item}><CheckIcon />{item}</li>)}</ul>
          </section>

          <section className={styles.watchSection}>
            <div className={styles.providerMark}><PlayIcon /></div>
            <div><strong>{movie.watchLabel}</strong><span>{movie.watchDetail}</span></div>
            <button type="button" onClick={() => { onClose(); onWatch(); }}>Watch<ChevronIcon /></button>
          </section>
          <p className={styles.dataCredit}>Movie metadata and imagery from TMDB · Availability region DE</p>
        </div>
      </section>
    </div>
  );
}

function ScoreDial({ score }: { score: number }) {
  return (
    <div className={styles.scoreDial} aria-label={`Match score ${score} out of 100`}>
      <svg viewBox="0 0 58 58" aria-hidden="true"><circle cx="29" cy="29" r="25" /><circle className={styles.scoreArc} cx="29" cy="29" r="25" pathLength="100" strokeDasharray="100" strokeDashoffset={100 - score} /></svg>
      <span><strong>{score}</strong><small>match</small></span>
    </div>
  );
}

function InfoIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5" /><path d="M12 11v5M12 8h.01" /></svg>; }
function PlayIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 7 8 5-8 5Z" /></svg>; }
function RefreshIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 8.5A8 8 0 1 0 20 14" /><path d="M19 4v4.5h-4.5" /></svg>; }
function CloseIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 7 10 10M17 7 7 17" /></svg>; }
function CheckIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4 10-10" /></svg>; }
function ChevronIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>; }
