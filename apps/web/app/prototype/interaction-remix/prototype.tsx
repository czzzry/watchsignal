"use client";

// Five throwaway WatchSignal interaction concepts, switchable with ?variant=A through E.

import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import styles from "./prototype.module.css";

type VariantKey = "A" | "B" | "C" | "D" | "E";
type Layer = "details" | "seen" | null;

type Movie = {
  title: string;
  year: string;
  runtime: string;
  genre: string;
  poster: string;
  score: number;
  reason: string;
};

const shortlist: Movie[] = [
  {
    title: "Arrival",
    year: "2016",
    runtime: "1h 56m",
    genre: "Drama · Sci-Fi",
    poster: "https://image.tmdb.org/t/p/w780/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
    score: 84,
    reason: "Thoughtful and tense, without going bleak.",
  },
  {
    title: "Knives Out",
    year: "2019",
    runtime: "2h 11m",
    genre: "Mystery · Comedy",
    poster: "https://image.tmdb.org/t/p/w500/pThyQovXQrw2m0s9x82twj48Jq4.jpg",
    score: 72,
    reason: "Lighter and faster, with a strong shared reaction.",
  },
  {
    title: "Past Lives",
    year: "2023",
    runtime: "1h 46m",
    genre: "Drama · Romance",
    poster: "https://image.tmdb.org/t/p/w500/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg",
    score: 61,
    reason: "Emotionally precise, but quieter than tonight's mood.",
  },
  {
    title: "The Grand Budapest Hotel",
    year: "2014",
    runtime: "1h 40m",
    genre: "Comedy · Adventure",
    poster: "https://image.tmdb.org/t/p/w500/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg",
    score: 52,
    reason: "Playful and beautiful, with a weaker shared signal.",
  },
  {
    title: "Edge of Tomorrow",
    year: "2014",
    runtime: "1h 53m",
    genre: "Action · Sci-Fi",
    poster: "https://image.tmdb.org/t/p/w500/uUHvlkLavotfGsNtosDy8ShsIYF.jpg",
    score: 38,
    reason: "Strong pace, but one clear no pulls it down.",
  },
];

const secondWave: Movie[] = [
  {
    title: "Palm Springs",
    year: "2020",
    runtime: "1h 30m",
    genre: "Comedy · Romance",
    poster: "https://image.tmdb.org/t/p/w342/yf5IuMW6GHghu39kxA0oFx7Bxmj.jpg",
    score: 79,
    reason: "Fast, funny, and more inventive than a standard comedy.",
  },
  {
    title: "The Nice Guys",
    year: "2016",
    runtime: "1h 56m",
    genre: "Comedy · Mystery",
    poster: "https://image.tmdb.org/t/p/w342/clq4So9spa9cXk3MZy2iMdqkxP2.jpg",
    score: 70,
    reason: "Loose, funny, and built around an easy double act.",
  },
  {
    title: "Hunt for the Wilderpeople",
    year: "2016",
    runtime: "1h 41m",
    genre: "Comedy · Adventure",
    poster: "https://image.tmdb.org/t/p/w342/hkmz9rxgcweizXNElozGeKwmAJE.jpg",
    score: 62,
    reason: "Warm and odd, with enough momentum for tonight.",
  },
  {
    title: "Game Night",
    year: "2018",
    runtime: "1h 40m",
    genre: "Comedy · Mystery",
    poster: "https://image.tmdb.org/t/p/w342/85R8LMyn9f2Lev2YPBF8Nughrkv.jpg",
    score: 53,
    reason: "The easiest watch, but less distinctive for both of you.",
  },
  {
    title: "The Menu",
    year: "2022",
    runtime: "1h 47m",
    genre: "Thriller · Comedy",
    poster: "https://image.tmdb.org/t/p/w342/v31MsWhF9WFh7Qooq6xSBbmJxoG.jpg",
    score: 44,
    reason: "Darkly funny, though it pushes past your requested lightness.",
  },
];

const variants: VariantKey[] = ["A", "B", "C", "D", "E"];
const variantNames: Record<VariantKey, string> = {
  A: "Signal reveal",
  B: "Quiet reaction",
  C: "Shortlist assembly",
  D: "Private handoff",
  E: "Second wave",
};

const variantReferences: Record<VariantKey, string> = {
  A: "MUBI · Flighty · Gentler Streak · Loóna",
  B: "Crouton · Things 3 · Opal",
  C: "CapWords · Endel",
  D: "Tiimo · Opal",
  E: "Arc Search · Flighty · Gentler Streak",
};

export function InteractionRemixPrototype() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requested = searchParams.get("variant")?.toUpperCase();
  const variant: VariantKey = variants.includes(requested as VariantKey) ? requested as VariantKey : "A";

  function chooseVariant(next: VariantKey) {
    router.replace(`/prototype/interaction-remix?variant=${next}`, { scroll: false });
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.matches("input, textarea, [contenteditable='true']")) return;
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      const current = variants.indexOf(variant);
      const offset = event.key === "ArrowRight" ? 1 : -1;
      chooseVariant(variants[(current + offset + variants.length) % variants.length]);
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [variant]);

  return (
    <main className={styles.studio} data-variant={variant}>
      <div className={styles.prototypeNotice}>Interaction remix · illustrative only</div>
      <div className={styles.phoneFrame}>
        {variant === "A" ? <SignalReveal /> : null}
        {variant === "B" ? <QuietReaction /> : null}
        {variant === "C" ? <ShortlistAssembly /> : null}
        {variant === "D" ? <PrivateHandoff /> : null}
        {variant === "E" ? <SecondWave /> : null}
      </div>
      <PrototypeSwitcher current={variant} onChange={chooseVariant} />
    </main>
  );
}

function SignalReveal() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [whyOpen, setWhyOpen] = useState(false);
  const [picked, setPicked] = useState(false);
  const movie = shortlist[activeIndex];
  const lead = activeIndex === 0 ? movie.score - shortlist[1].score : movie.score - shortlist[Math.min(activeIndex + 1, shortlist.length - 1)].score;

  return (
    <section className={`${styles.screen} ${styles.revealScreen}`}>
      <img key={movie.title} className={styles.revealPoster} src={movie.poster} alt={`${movie.title} movie poster`} />
      <div className={styles.revealShade} />
      <Header trailing={`${activeIndex + 1} of 5`} />

      <div className={styles.revealCopy}>
        <ScoreRing score={movie.score} />
        <p className={styles.tonightLabel}>{activeIndex === 0 ? `Tonight's strongest match · ${lead} points clear` : `Ranked #${activeIndex + 1}`}</p>
        <h1 className={styles.cinematicTitle}>{movie.title}</h1>
        <p className={styles.meta}>{movie.year} · {movie.runtime} · {movie.genre}</p>
        <p className={styles.revealReason}>{movie.reason}</p>

        <div className={styles.revealRail} aria-label="Ranked movies">
          {shortlist.map((item, index) => (
            <button key={item.title} className={index === activeIndex ? styles.revealRailActive : ""} type="button" onClick={() => { setActiveIndex(index); setWhyOpen(false); setPicked(false); }} aria-label={`${item.title}, score ${item.score}`}>
              <img src={item.poster} alt="" />
              <span>{item.score}</span>
            </button>
          ))}
        </div>

        <div className={styles.revealActions}>
          <button className={styles.secondaryButton} type="button" onClick={() => setWhyOpen(true)}>Why {movie.score}?</button>
          <button className={styles.lightButton} type="button" onClick={() => setPicked(!picked)}>{picked ? <><CheckIcon />Tonight&apos;s movie</> : <>Pick this<ChevronIcon /></>}</button>
        </div>
        <button className={styles.textAction} type="button">None of these · Find five more</button>
      </div>

      {picked ? <div className={styles.confirmationToast}>Picked for tonight <button type="button" onClick={() => setPicked(false)}>Undo</button></div> : null}
      {whyOpen ? <WhySheet movie={movie} onClose={() => setWhyOpen(false)} /> : null}
    </section>
  );
}

function WhySheet({ movie, onClose }: { movie: Movie; onClose: () => void }) {
  return (
    <Layer onClose={onClose} label={`Why ${movie.title} scored ${movie.score}`}>
      <div className={styles.sheetHeading}>
        <div><span>Why {movie.score}</span><h2>{movie.title}</h2></div>
        <button type="button" onClick={onClose} aria-label="Close">×</button>
      </div>
      <p className={styles.scoreContext}>{movie.score === 84 ? "12 points above your next option." : `Ranked #${shortlist.findIndex((item) => item.title === movie.title) + 1} tonight.`}</p>
      <ul className={styles.factorList}>
        <li><CheckIcon /><span><strong>Both interested</strong><small>The strongest shared signal</small></span></li>
        <li><CheckIcon /><span><strong>Mood fit</strong><small>Thoughtful, not bleak</small></span></li>
        <li><CheckIcon /><span><strong>Watchable now</strong><small>Included on Prime Video</small></span></li>
        <li className={styles.factorPenalty}><MinusIcon /><span><strong>Small penalty</strong><small>Slightly slower than requested</small></span></li>
      </ul>
      <button className={styles.darkButton} type="button" onClick={onClose}>Got it</button>
    </Layer>
  );
}

function QuietReaction() {
  const [reaction, setReaction] = useState<string | null>(null);
  const [layer, setLayer] = useState<Layer>(null);
  const [memory, setMemory] = useState<string | null>(null);
  const movie = shortlist[1];

  return (
    <section className={`${styles.screen} ${styles.reactionScreen}`}>
      <img className={styles.reactionPoster} src={movie.poster} alt={`${movie.title} movie poster`} />
      <div className={styles.reactionShade} />
      <header className={styles.reactionHeader}>
        <button type="button" aria-label="Back"><BackIcon /></button>
        <div className={styles.progressLine}><i><b /></i><span>1 / 5</span></div>
        <span className={styles.privateTag}><LockIcon />Private</span>
      </header>

      <div className={styles.reactionCopy}>
        <h1 className={styles.cinematicTitle}>{movie.title}</h1>
        <p className={styles.meta}>{movie.year} · {movie.runtime} · {movie.genre}</p>
        <p className={styles.reactionReason}>{movie.reason}</p>
        {memory ? <p className={styles.savedLine}><CheckIcon />Seen memory: {memory}</p> : null}

        <div className={styles.utilityRow}>
          <button type="button" onClick={() => setLayer("details")}><InfoIcon />More</button>
          <button type="button" onClick={() => setLayer("seen")}><EyeIcon />Seen before</button>
        </div>

        <div className={styles.reactionRow} aria-label="Your private reaction">
          {["Interested", "Maybe", "No"].map((value) => (
            <button key={value} className={reaction === value ? styles.reactionActive : ""} type="button" onClick={() => setReaction(value)}>
              <ReactionMark value={value} active={reaction === value} />
              <span>{reaction === value ? "Saved" : value}</span>
            </button>
          ))}
        </div>
        <p className={styles.privateCopy}>{reaction ? `${reaction} saved privately` : "Choose your honest reaction"}</p>
      </div>

      {layer === "details" ? (
        <Layer onClose={() => setLayer(null)} label="Movie details">
          <div className={styles.sheetHeading}><div><span>More</span><h2>Why show this?</h2></div><button type="button" onClick={() => setLayer(null)} aria-label="Close">×</button></div>
          <p className={styles.sheetParagraph}>A quick, playful mystery that gives you something to solve without feeling heavy.</p>
          <dl className={styles.detailList}><div><dt>Cast</dt><dd>Daniel Craig · Ana de Armas</dd></div><div><dt>Audio</dt><dd>English</dd></div><div><dt>Watch</dt><dd>Prime Video tonight</dd></div></dl>
          <button className={styles.darkButton} type="button" onClick={() => setLayer(null)}>Done</button>
        </Layer>
      ) : null}
      {layer === "seen" ? (
        <Layer onClose={() => setLayer(null)} label="Seen memory">
          <div className={styles.sheetHeading}><div><span>Memory</span><h2>You&apos;ve seen it?</h2></div><button type="button" onClick={() => setLayer(null)} aria-label="Close">×</button></div>
          <div className={styles.memoryList}>
            {["Loved it", "It was fine", "Not for me", "I forget"].map((value) => <button key={value} type="button" onClick={() => { setMemory(value); setLayer(null); }}>{value}<ChevronIcon /></button>)}
          </div>
        </Layer>
      ) : null}
    </section>
  );
}

function ShortlistAssembly() {
  const [run, setRun] = useState(0);
  const [step, setStep] = useState(0);

  useEffect(() => {
    setStep(0);
    const timers = [
      window.setTimeout(() => setStep(1), 520),
      window.setTimeout(() => setStep(2), 1120),
      window.setTimeout(() => setStep(3), 1780),
    ];
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [run]);

  const status = ["Reading your mood", "Balancing both tastes", "Checking Prime Video", "Your five are ready"][step];

  return (
    <section className={`${styles.screen} ${styles.assemblyScreen}`}>
      <Header trailing="Tonight" />
      <svg className={styles.signalField} viewBox="0 0 390 430" aria-hidden="true">
        <path d="M-20 190 C70 80 120 310 210 180 S350 70 420 210" />
        <path d="M-30 225 C60 115 125 340 220 215 S345 105 430 245" />
        <path d="M-20 255 C80 165 145 360 235 250 S350 160 420 280" />
      </svg>

      <div className={`${styles.posterAssembly} ${styles[`assemblyStep${step}`]}`} data-step={step}>
        {shortlist.map((movie, index) => <img key={movie.title} style={{ "--poster-index": index } as CSSProperties} src={movie.poster} alt="" />)}
        <span className={styles.assemblyPulse} />
      </div>

      <div className={styles.assemblyCopy}>
        <div className={styles.assemblyStatus}><span>{step < 3 ? "Building" : "Ready"}</span><strong>{status}</strong></div>
        <div className={styles.buildRail}><i style={{ transform: `scaleX(${0.25 + step * 0.25})` }} /></div>
        <div className={styles.intentTokens}><span>Thoughtful</span><span>Not bleak</span><span>Under 2h 15m</span></div>
        {step === 3 ? (
          <button className={styles.lightButton} type="button">Open Cezary&apos;s pass<ChevronIcon /></button>
        ) : (
          <p className={styles.buildNote}>Scores will be spaced and ranked, not rounded into false certainty.</p>
        )}
        <button className={styles.rebuildButton} type="button" onClick={() => setRun((value) => value + 1)}>Replay transition</button>
      </div>
    </section>
  );
}

function PrivateHandoff() {
  const [open, setOpen] = useState(false);

  if (open) {
    return (
      <section className={`${styles.screen} ${styles.handoffReady}`}>
        <Header trailing="Sophie · Private" />
        <div className={styles.readyPosterStack} aria-hidden="true">
          {shortlist.slice(0, 3).map((movie, index) => <img key={movie.title} src={movie.poster} alt="" data-position={index} />)}
          <span><LockIcon /></span>
        </div>
        <div className={styles.readyCopy}>
          <p>Sophie&apos;s turn</p>
          <h1 className={styles.cinematicTitle}>Your five are ready.</h1>
          <span>Cezary&apos;s answers stay hidden</span>
          <button className={styles.lightButton} type="button">Start 1 of 5<ChevronIcon /></button>
        </div>
      </section>
    );
  }

  return (
    <section className={`${styles.screen} ${styles.handoffScreen}`}>
      <Header trailing="Pass the phone" />
      <div className={styles.handoffCopy}>
        <p className={styles.handoffCue}><LockIcon />Cezary&apos;s answers sealed</p>
        <h1 className={styles.cinematicTitle}>Sophie is next.</h1>

        <ol className={styles.passTimeline}>
          <li className={styles.timelineDone}><span><CheckIcon /></span><div><strong>Cezary</strong><small>Five private reactions saved</small></div></li>
          <li className={styles.timelineNow}><span>2</span><div><strong>Sophie</strong><small>Same five movies, fresh order</small></div></li>
          <li><span>3</span><div><strong>Reveal</strong><small>Unlocks after both passes</small></div></li>
        </ol>

        <button className={styles.lightButton} type="button" onClick={() => setOpen(true)}>I&apos;m Sophie<ChevronIcon /></button>
        <p className={styles.handoffFootnote}>The screen changes before any answers appear.</p>
      </div>
    </section>
  );
}

function SecondWave() {
  const [mood, setMood] = useState("Lighter and faster");
  const [refined, setRefined] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const movies = generated ? secondWave : shortlist.slice(1);
  const active = movies[Math.min(activeIndex, movies.length - 1)];

  return (
    <section className={`${styles.screen} ${styles.waveScreen}`}>
      <Header trailing={generated ? "Second wave" : "Your shortlist"} />
      <div className={styles.waveCopy}>
        <div className={styles.waveHeading}>
          <span>{generated ? "Five new options" : "Arrival wasn't it"}</span>
          <h1>{generated ? "A lighter second wave." : "Keep looking."}</h1>
        </div>

        {refined ? (
          <button className={styles.intentResult} type="button" onClick={() => setRefined(false)}><SparkIcon /><span><small>Now aiming for</small><strong>{mood}</strong></span><EditIcon /></button>
        ) : (
          <div className={styles.refineBar}>
            <input value={mood} onChange={(event) => setMood(event.target.value)} aria-label="Refine tonight's mood" />
            <button type="button" onClick={() => setRefined(true)}>Use</button>
          </div>
        )}

        <div className={styles.rankedList} aria-label="Ranked alternatives">
          {movies.map((movie, index) => (
            <button key={movie.title} className={index === activeIndex ? styles.rankedActive : ""} type="button" onClick={() => setActiveIndex(index)}>
              <img src={movie.poster} alt="" />
              <span className={styles.rankNumber}>{index + 1}</span>
              <span className={styles.rankCopy}><strong>{movie.title}</strong><small>{movie.year} · {movie.runtime}</small></span>
              <span className={styles.rankScore}>{movie.score}</span>
            </button>
          ))}
        </div>

        <div className={styles.activeReason}><span>{active.score} match</span><p>{active.reason}</p></div>
        {!generated ? (
          <button className={styles.lightButton} type="button" onClick={() => { setGenerated(true); setRefined(true); setActiveIndex(0); }}>Find five more<SparkIcon /></button>
        ) : (
          <button className={styles.lightButton} type="button">Pick {active.title}<ChevronIcon /></button>
        )}
      </div>
    </section>
  );
}

function Header({ trailing }: { trailing: string }) {
  return <header className={styles.header}><div className={styles.brand}><span>W</span><strong>WatchSignal</strong></div><p>{trailing}</p></header>;
}

function ScoreRing({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 27;
  return (
    <div className={styles.scoreRing} aria-label={`Match score ${score} out of 100`}>
      <svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="27" /><circle className={styles.scoreValue} cx="32" cy="32" r="27" strokeDasharray={circumference} strokeDashoffset={circumference * (1 - score / 100)} /></svg>
      <span><strong>{score}</strong><small>match</small></span>
    </div>
  );
}

function Layer({ children, onClose, label }: { children: ReactNode; onClose: () => void; label: string }) {
  return <div className={styles.layer}><button className={styles.layerBackdrop} type="button" aria-label="Close" onClick={onClose} /><section className={styles.sheet} aria-label={label}>{children}</section></div>;
}

function PrototypeSwitcher({ current, onChange }: { current: VariantKey; onChange: (variant: VariantKey) => void }) {
  const currentIndex = variants.indexOf(current);
  return (
    <nav className={styles.switcher} aria-label="Remix prototype variants">
      <button type="button" onClick={() => onChange(variants[(currentIndex - 1 + variants.length) % variants.length])} aria-label="Previous concept">←</button>
      <div><span>{current} of 5 · {variantReferences[current]}</span><strong>{variantNames[current]}</strong></div>
      <button type="button" onClick={() => onChange(variants[(currentIndex + 1) % variants.length])} aria-label="Next concept">→</button>
    </nav>
  );
}

function ReactionMark({ value, active }: { value: string; active: boolean }) {
  if (value === "Interested") return <SparkIcon />;
  if (value === "Maybe") return <span className={styles.maybeMark}>{active ? "●" : "○"}</span>;
  return <CloseIcon />;
}

function ChevronIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7" /></svg>; }
function BackIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 5-7 7 7 7" /></svg>; }
function LockIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="3" /><path d="M8.5 10V7.5a3.5 3.5 0 0 1 7 0V10" /></svg>; }
function CheckIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6" /></svg>; }
function MinusIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 12h12" /></svg>; }
function InfoIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7.5v.1" /></svg>; }
function EyeIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12s3.3-5 9-5 9 5 9 5-3.3 5-9 5-9-5-9-5Z" /><circle cx="12" cy="12" r="2.5" /></svg>; }
function SparkIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z" /></svg>; }
function EditIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 20 4-.8L19 8.3 15.7 5 4.8 15.9 4 20Z" /><path d="m13.8 6.9 3.3 3.3" /></svg>; }
function CloseIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>; }
