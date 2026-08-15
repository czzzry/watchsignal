"use client";

// Three flagship filmstrip variants of the post-ballot result, switchable via ?variant=.

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import styles from "./prototype.module.css";

type VariantKey = "A" | "B" | "C";

type Movie = {
  title: string;
  year: string;
  runtime: string;
  genres: string;
  poster: string;
  score: number;
  reactions: string;
  reason: string;
  availability: string;
};

const movies: Movie[] = [
  {
    title: "Arrival",
    year: "2016",
    runtime: "1h 56m",
    genres: "Drama · Sci-Fi",
    poster: "https://image.tmdb.org/t/p/w780/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
    score: 86,
    reactions: "Both interested",
    reason: "Thoughtful and tense, without going bleak.",
    availability: "Included tonight",
  },
  {
    title: "Knives Out",
    year: "2019",
    runtime: "2h 11m",
    genres: "Mystery · Comedy",
    poster: "https://image.tmdb.org/t/p/w342/pThyQovXQrw2m0s9x82twj48Jq4.jpg",
    score: 74,
    reactions: "Interested + maybe",
    reason: "Lighter, faster, and still gives you a puzzle.",
    availability: "Available tonight",
  },
  {
    title: "Past Lives",
    year: "2023",
    runtime: "1h 46m",
    genres: "Drama · Romance",
    poster: "https://image.tmdb.org/t/p/w342/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg",
    score: 63,
    reactions: "Maybe + interested",
    reason: "The emotional choice, with less momentum tonight.",
    availability: "Available tonight",
  },
  {
    title: "The Grand Budapest Hotel",
    year: "2014",
    runtime: "1h 40m",
    genres: "Comedy · Adventure",
    poster: "https://image.tmdb.org/t/p/w342/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg",
    score: 55,
    reactions: "Both maybe",
    reason: "Playful and beautiful, with a weaker mood match.",
    availability: "Available tonight",
  },
  {
    title: "Edge of Tomorrow",
    year: "2014",
    runtime: "1h 53m",
    genres: "Action · Sci-Fi",
    poster: "https://image.tmdb.org/t/p/w342/uUHvlkLavotfGsNtosDy8ShsIYF.jpg",
    score: 42,
    reactions: "Interested + no",
    reason: "Strong pace, but one reaction pulls it down.",
    availability: "Available tonight",
  },
];

const variantNames: Record<VariantKey, string> = {
  A: "Afterglow",
  B: "Screening room",
  C: "Spotlight",
};

export function NorthStarResultPrototype() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requested = searchParams.get("variant")?.toUpperCase();
  const variant: VariantKey = requested === "B" || requested === "C" ? requested : "A";

  function chooseVariant(next: VariantKey) {
    router.replace(`/prototype/north-star-result?variant=${next}`, { scroll: false });
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.matches("input, textarea, [contenteditable='true']")) return;
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      const order: VariantKey[] = ["A", "B", "C"];
      const current = order.indexOf(variant);
      const offset = event.key === "ArrowRight" ? 1 : -1;
      chooseVariant(order[(current + offset + order.length) % order.length]);
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [variant]);

  return (
    <main className={styles.studio} data-variant={variant}>
      <div className={styles.prototypeNotice}>Result prototype · scores are illustrative</div>
      <div className={styles.phoneFrame}>
        {variant === "A" ? <Afterglow /> : null}
        {variant === "B" ? <ScreeningRoom /> : null}
        {variant === "C" ? <Spotlight /> : null}
      </div>
      <PrototypeSwitcher current={variant} onChange={chooseVariant} />
    </main>
  );
}

export function Afterglow() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [continuing, setContinuing] = useState(false);
  const movie = movies[activeIndex];

  if (continuing) {
    return <NextFiveState skin="afterglow" onBack={() => setContinuing(false)} />;
  }

  return (
    <section className={`${styles.screen} ${styles.afterglow}`}>
      <img key={movie.title} className={styles.afterglowPoster} src={movie.poster} alt={`${movie.title} movie poster`} />
      <div className={styles.afterglowAtmosphere} />
      <ResultHeader position={activeIndex + 1} />

      <div className={styles.afterglowContent}>
        <ScoreDial score={movie.score} />
        <p className={styles.resultCue}>{activeIndex === 0 ? "Tonight's strongest match" : `Your #${activeIndex + 1} match`}</p>
        <h1 className={styles.cinematicTitle}>{movie.title}</h1>
        <MovieMeta movie={movie} light />
        <p className={styles.matchReason}><strong>{movie.reactions}</strong><span>{movie.reason}</span></p>
        <PosterFilmstrip activeIndex={activeIndex} onSelect={setActiveIndex} />
        <ResultActions onMore={() => setContinuing(true)} />
      </div>
    </section>
  );
}

function ScreeningRoom() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [continuing, setContinuing] = useState(false);
  const movie = movies[activeIndex];

  if (continuing) {
    return <NextFiveState skin="screening" onBack={() => setContinuing(false)} />;
  }

  return (
    <section className={`${styles.screen} ${styles.screeningRoom}`}>
      <ResultHeader position={activeIndex + 1} />

      <figure className={styles.screeningFrame}>
        <img key={movie.title} src={movie.poster} alt={`${movie.title} movie poster`} />
        <div className={styles.frameShade} />
        <ScoreDial score={movie.score} compact />
        <figcaption>{movie.reactions}</figcaption>
      </figure>

      <div className={styles.screeningCopy}>
        <h1>{movie.title}</h1>
        <MovieMeta movie={movie} light />
        <p>{movie.reason}</p>
      </div>

      <NumberedReel activeIndex={activeIndex} onSelect={setActiveIndex} />
      <div className={styles.screeningActions}><ResultActions onMore={() => setContinuing(true)} /></div>
    </section>
  );
}

function Spotlight() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [continuing, setContinuing] = useState(false);
  const movie = movies[activeIndex];
  const before = movies[(activeIndex - 1 + movies.length) % movies.length];
  const after = movies[(activeIndex + 1) % movies.length];

  if (continuing) {
    return <NextFiveState skin="spotlight" onBack={() => setContinuing(false)} />;
  }

  return (
    <section className={`${styles.screen} ${styles.spotlight}`}>
      <div className={styles.spotlightGlow} />
      <ResultHeader position={activeIndex + 1} />

      <div className={styles.posterCarousel}>
        <button className={`${styles.peekPoster} ${styles.peekBefore}`} type="button" onClick={() => setActiveIndex((activeIndex - 1 + movies.length) % movies.length)} aria-label={`Previous: ${before.title}`}>
          <img src={before.poster} alt="" />
        </button>
        <article className={styles.spotlightPoster}>
          <img key={movie.title} src={movie.poster} alt={`${movie.title} movie poster`} />
          <ScoreDial score={movie.score} compact />
        </article>
        <button className={`${styles.peekPoster} ${styles.peekAfter}`} type="button" onClick={() => setActiveIndex((activeIndex + 1) % movies.length)} aria-label={`Next: ${after.title}`}>
          <img src={after.poster} alt="" />
        </button>
      </div>

      <div className={styles.spotlightCopy}>
        <h1 className={styles.cinematicTitle}>{movie.title}</h1>
        <MovieMeta movie={movie} light />
        <p><strong>{movie.reactions}</strong> · {movie.reason}</p>
      </div>

      <ScoreTrack activeIndex={activeIndex} onSelect={setActiveIndex} />
      <div className={styles.spotlightActions}><ResultActions onMore={() => setContinuing(true)} /></div>
    </section>
  );
}

function PosterFilmstrip({ activeIndex, onSelect }: { activeIndex: number; onSelect: (index: number) => void }) {
  return (
    <div className={styles.posterFilmstrip} aria-label="Ranked movie shortlist">
      {movies.map((movie, index) => (
        <button
          key={movie.title}
          className={index === activeIndex ? styles.posterFilmActive : ""}
          type="button"
          onClick={() => onSelect(index)}
          aria-label={`${index + 1}. ${movie.title}, match score ${movie.score}`}
        >
          <img src={movie.poster} alt="" />
          <span>{movie.score}</span>
        </button>
      ))}
    </div>
  );
}

function NumberedReel({ activeIndex, onSelect }: { activeIndex: number; onSelect: (index: number) => void }) {
  return (
    <div className={styles.numberedReel} aria-label="Ranked movie shortlist">
      {movies.map((movie, index) => (
        <button
          key={movie.title}
          className={index === activeIndex ? styles.numberedReelActive : ""}
          type="button"
          onClick={() => onSelect(index)}
          aria-label={`${index + 1}. ${movie.title}, match score ${movie.score}`}
        >
          <img src={movie.poster} alt="" />
          <span><small>0{index + 1}</small><strong>{movie.score}</strong></span>
        </button>
      ))}
    </div>
  );
}

function ScoreTrack({ activeIndex, onSelect }: { activeIndex: number; onSelect: (index: number) => void }) {
  return (
    <div className={styles.scoreTrack} aria-label="All match scores">
      <i aria-hidden="true" />
      {movies.map((movie, index) => (
        <button
          key={movie.title}
          className={index === activeIndex ? styles.scoreTrackActive : ""}
          type="button"
          onClick={() => onSelect(index)}
          aria-label={`${index + 1}. ${movie.title}, match score ${movie.score}`}
        >
          <span>{movie.score}</span><b />
        </button>
      ))}
    </div>
  );
}

function ResultActions({ onMore }: { onMore: () => void }) {
  return (
    <div className={styles.resultActions} role="group" aria-label="Movie result actions">
      <button className={styles.watchAction} type="button"><PlayIcon /><span>Watch this</span></button>
      <button className={styles.moreAction} type="button" onClick={onMore}><RefreshIcon /><span>5 more</span></button>
    </div>
  );
}

function NextFiveState({ skin, onBack }: { skin: "afterglow" | "screening" | "spotlight"; onBack: () => void }) {
  const [choice, setChoice] = useState<"same" | "different" | "steer">("same");
  const [finding, setFinding] = useState(false);

  return (
    <section className={`${styles.screen} ${styles.nextFive} ${styles[`nextFive_${skin}`]}`}>
      <header className={styles.nextFiveHeader}>
        <button type="button" onClick={onBack} aria-label="Back to current results"><BackIcon /></button>
        <BrandMark />
        <span />
      </header>

      <div className={styles.nextFiveBody}>
        <div className={styles.nextFiveSignal} aria-hidden="true"><RefreshIcon /></div>
        <h1>Five more,<br />your way.</h1>
        <p>Your reactions stay. These five will not repeat.</p>

        <div className={styles.nextFiveChoices} role="radiogroup" aria-label="Direction for five more picks">
          <ChoiceRow selected={choice === "same"} title="Same direction" detail="Fresh movies, same mood" onClick={() => setChoice("same")} />
          <ChoiceRow selected={choice === "different"} title="Different direction" detail="Move away from this batch" onClick={() => setChoice("different")} />
          <ChoiceRow selected={choice === "steer"} title="Add a steer" detail="Lighter, stranger, shorter..." onClick={() => setChoice("steer")} />
        </div>

        {choice === "steer" ? <input className={styles.steerInput} aria-label="Describe what to change" placeholder="What should change?" autoFocus /> : null}

        <button className={styles.findAction} type="button" onClick={() => setFinding(true)} disabled={finding}>
          {finding ? <><span className={styles.loadingMark} aria-hidden="true" />Finding five new matches</> : <>Find 5 new matches<ChevronIcon /></>}
        </button>
      </div>
    </section>
  );
}

function ChoiceRow({ selected, title, detail, onClick }: { selected: boolean; title: string; detail: string; onClick: () => void }) {
  return (
    <button className={selected ? styles.choiceSelected : ""} type="button" role="radio" aria-checked={selected} onClick={onClick}>
      <span><strong>{title}</strong><small>{detail}</small></span>
      <i aria-hidden="true">{selected ? "✓" : ""}</i>
    </button>
  );
}

function ScoreDial({ score, compact = false }: { score: number; compact?: boolean }) {
  const radius = compact ? 21 : 27;

  return (
    <div className={`${styles.scoreDial} ${compact ? styles.scoreDialCompact : ""}`} aria-label={`Match score ${score} out of 100`}>
      <svg viewBox="0 0 68 68" aria-hidden="true">
        <circle className={styles.scoreDialBase} cx="34" cy="34" r={radius} />
        <circle className={styles.scoreDialValue} cx="34" cy="34" r={radius} pathLength="100" strokeDasharray="100" strokeDashoffset={100 - score} />
      </svg>
      <span><strong>{score}</strong><small>match</small></span>
    </div>
  );
}

function ResultHeader({ position }: { position: number }) {
  return (
    <header className={styles.resultHeader}>
      <BrandMark />
      <span>Result {position} / 5</span>
    </header>
  );
}

function BrandMark() {
  return <div className={styles.brand}><span>W</span><strong>WatchSignal</strong></div>;
}

function MovieMeta({ movie, light = false }: { movie: Movie; light?: boolean }) {
  return <p className={`${styles.movieMeta} ${light ? styles.movieMetaLight : ""}`}>{movie.year} · {movie.runtime} · {movie.genres} · {movie.availability}</p>;
}

function PlayIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8.5 6.5 18 12l-9.5 5.5z" /></svg>;
}

function RefreshIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 8.5A8 8 0 1 0 20 14" /><path d="M19 4v4.5h-4.5" /></svg>;
}

function BackIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>;
}

function ChevronIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>;
}

function PrototypeSwitcher({ current, onChange }: { current: VariantKey; onChange: (value: VariantKey) => void }) {
  const order: VariantKey[] = ["A", "B", "C"];
  const index = order.indexOf(current);

  return (
    <nav className={styles.switcher} aria-label="Result prototype variants">
      <button type="button" onClick={() => onChange(order[(index + 2) % 3])} aria-label="Previous variant">←</button>
      <div><span>Result {current}</span><strong>{variantNames[current]}</strong></div>
      <button type="button" onClick={() => onChange(order[(index + 1) % 3])} aria-label="Next variant">→</button>
    </nav>
  );
}
