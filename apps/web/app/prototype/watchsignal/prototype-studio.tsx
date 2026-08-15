"use client";

// Three throwaway WatchSignal motion systems, switchable via ?variant=.

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import styles from "./prototype.module.css";

type VariantKey = "A" | "B" | "C";
type Reaction = "interested" | "maybe" | "no";
type Stage = "setup" | "building" | "reaction" | "sealing" | "handoff" | "matching" | "reveal";
type SaveState = "idle" | "saving" | "saved";

type Candidate = {
  id: string;
  title: string;
  year: string;
  runtime: string;
  tone: string;
  reason: string;
  poster: string;
  score: number;
};

const candidates: Candidate[] = [
  {
    id: "arrival",
    title: "Arrival",
    year: "2016",
    runtime: "1h 56m",
    tone: "Smart, tense, emotional",
    reason: "A thoughtful mystery with momentum and a huge emotional landing.",
    poster: "/concept-arrival-poster.png",
    score: 94,
  },
  {
    id: "knives-out",
    title: "Knives Out",
    year: "2019",
    runtime: "2h 10m",
    tone: "Witty, twisty, bright",
    reason: "A crowd-pleasing mystery with sharp jokes and almost no setup tax.",
    poster: "/concept-knives-out-poster.svg",
    score: 91,
  },
];

const variantNames: Record<VariantKey, string> = {
  A: "Precise continuity",
  B: "Cinematic pulse",
  C: "Playful signals",
};

const stageLabels: Record<Stage, string> = {
  setup: "Tonight",
  building: "Building shortlist",
  reaction: "Private picks",
  sealing: "Sealing ballot",
  handoff: "Private handoff",
  matching: "Finding overlap",
  reveal: "Shared result",
};

const reactionLabels: Record<Reaction, string> = {
  no: "No",
  maybe: "Maybe",
  interested: "Interested",
};

export function PrototypeStudio() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const requested = searchParams.get("variant")?.toUpperCase();
  const variant: VariantKey = requested === "B" || requested === "C" ? requested : "A";

  function chooseVariant(next: VariantKey) {
    router.replace(`/prototype/watchsignal?variant=${next}`, { scroll: false });
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.matches("input, textarea, [contenteditable='true']")) return;
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      const order: VariantKey[] = ["A", "B", "C"];
      const current = order.indexOf(variant);
      const delta = event.key === "ArrowRight" ? 1 : -1;
      chooseVariant(order[(current + delta + order.length) % order.length]);
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [variant]);

  return (
    <main className={styles.studio}>
      <div className={styles.prototypeNotice}>Motion prototype - no data is saved</div>
      <div className={styles.phoneFrame} key={variant}>
        <MotionFlow variant={variant} />
      </div>
      <PrototypeSwitcher current={variant} onChange={chooseVariant} />
    </main>
  );
}

function PrototypeSwitcher({ current, onChange }: { current: VariantKey; onChange: (value: VariantKey) => void }) {
  const order: VariantKey[] = ["A", "B", "C"];
  const index = order.indexOf(current);

  return (
    <nav className={styles.switcher} aria-label="Motion prototype variants">
      <button type="button" onClick={() => onChange(order[(index + 2) % 3])} aria-label="Previous motion system">
        ←
      </button>
      <div>
        <span>Motion {current}</span>
        <strong>{variantNames[current]}</strong>
      </div>
      <button type="button" onClick={() => onChange(order[(index + 1) % 3])} aria-label="Next motion system">
        →
      </button>
    </nav>
  );
}

function MotionFlow({ variant }: { variant: VariantKey }) {
  const [stage, setStage] = useState<Stage>("setup");
  const [leaving, setLeaving] = useState(false);
  const [actorIndex, setActorIndex] = useState(0);
  const [movieIndex, setMovieIndex] = useState(0);
  const [pendingReaction, setPendingReaction] = useState<Reaction | null>(null);
  const [savedVotes, setSavedVotes] = useState(0);
  const [waitStep, setWaitStep] = useState(0);
  const [startBusy, setStartBusy] = useState(false);
  const [handoffBusy, setHandoffBusy] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [seenSaved, setSeenSaved] = useState(false);
  const [screenKey, setScreenKey] = useState(0);
  const timers = useRef<number[]>([]);

  const actor = actorIndex === 0 ? "Cezary" : "Sophie";
  const exitDuration = variant === "A" ? 180 : variant === "B" ? 420 : 300;

  function later(callback: () => void, delay: number) {
    const timer = window.setTimeout(callback, delay);
    timers.current.push(timer);
  }

  function moveTo(next: Stage, before?: () => void) {
    setLeaving(true);
    later(() => {
      before?.();
      setStage(next);
      setLeaving(false);
      setScreenKey((current) => current + 1);
    }, exitDuration);
  }

  useEffect(() => {
    return () => timers.current.forEach((timer) => window.clearTimeout(timer));
  }, []);

  useEffect(() => {
    setWaitStep(0);

    if (stage === "building") {
      const one = window.setTimeout(() => setWaitStep(1), 650);
      const two = window.setTimeout(() => setWaitStep(2), 1320);
      const done = window.setTimeout(() => moveTo("reaction"), 2150);
      return () => [one, two, done].forEach((timer) => window.clearTimeout(timer));
    }

    if (stage === "sealing") {
      const one = window.setTimeout(() => setWaitStep(1), 720);
      const two = window.setTimeout(() => setWaitStep(2), 1440);
      const done = window.setTimeout(() => moveTo("handoff"), 2320);
      return () => [one, two, done].forEach((timer) => window.clearTimeout(timer));
    }

    if (stage === "matching") {
      const one = window.setTimeout(() => setWaitStep(1), 820);
      const two = window.setTimeout(() => setWaitStep(2), 1680);
      const done = window.setTimeout(() => moveTo("reveal"), 2850);
      return () => [one, two, done].forEach((timer) => window.clearTimeout(timer));
    }
  }, [stage, variant]);

  function startNight() {
    if (startBusy) return;
    setStartBusy(true);
    later(() => moveTo("building"), 720);
  }

  function react(reaction: Reaction) {
    if (pendingReaction) return;
    setPendingReaction(reaction);
    setSavedVotes((current) => current + 1);
    const hold = variant === "A" ? 420 : variant === "B" ? 760 : 590;

    later(() => {
      if (movieIndex < candidates.length - 1) {
        setMovieIndex((current) => current + 1);
        setPendingReaction(null);
        setSeenSaved(false);
        setScreenKey((current) => current + 1);
        return;
      }

      setPendingReaction(null);
      moveTo(actorIndex === 0 ? "sealing" : "matching");
    }, hold);
  }

  function unlockSecondPass() {
    if (handoffBusy) return;
    setHandoffBusy(true);
    later(() => {
      moveTo("reaction", () => {
        setActorIndex(1);
        setMovieIndex(0);
        setHandoffBusy(false);
        setSeenSaved(false);
      });
    }, 760);
  }

  function saveWinner() {
    if (saveState !== "idle") return;
    setSaveState("saving");
    later(() => setSaveState("saved"), 1250);
  }

  function restart() {
    timers.current.forEach((timer) => window.clearTimeout(timer));
    timers.current = [];
    setStage("setup");
    setLeaving(false);
    setActorIndex(0);
    setMovieIndex(0);
    setPendingReaction(null);
    setSavedVotes(0);
    setWaitStep(0);
    setStartBusy(false);
    setHandoffBusy(false);
    setSaveState("idle");
    setSeenSaved(false);
    setScreenKey((current) => current + 1);
  }

  const motionClass = variant === "A" ? styles.motionPrecise : variant === "B" ? styles.motionCinematic : styles.motionPlayful;
  const stageClass = `${styles.screen} ${leaving ? styles.screenLeaving : styles.screenEntering}`;

  return (
    <section className={`${styles.motionFlow} ${motionClass}`} data-motion={variant}>
      <header className={styles.appHeader}>
        <div className={styles.wordmark}><span>W</span> WatchSignal</div>
        <div className={styles.stageStatus} aria-live="polite">
          <i />
          {stageLabels[stage]}
        </div>
      </header>

      <div className={styles.flowProgress} aria-hidden="true">
        <span style={{ width: `${stageProgress(stage)}%` }} />
      </div>

      <div className={styles.screenViewport}>
        <div className={stageClass} key={`${stage}-${screenKey}`}>
          {stage === "setup" ? <SetupScreen busy={startBusy} variant={variant} onStart={startNight} /> : null}
          {stage === "building" ? <WaitScreen stage="building" step={waitStep} variant={variant} /> : null}
          {stage === "reaction" ? (
            <ReactionScreen
              actor={actor}
              actorIndex={actorIndex}
              candidate={candidates[movieIndex]}
              movieIndex={movieIndex}
              pending={pendingReaction}
              savedVotes={savedVotes}
              seenSaved={seenSaved}
              onSeen={() => setSeenSaved((current) => !current)}
              onReact={react}
            />
          ) : null}
          {stage === "sealing" ? <WaitScreen stage="sealing" step={waitStep} variant={variant} /> : null}
          {stage === "handoff" ? <HandoffScreen busy={handoffBusy} variant={variant} onUnlock={unlockSecondPass} /> : null}
          {stage === "matching" ? <WaitScreen stage="matching" step={waitStep} variant={variant} /> : null}
          {stage === "reveal" ? <RevealScreen saveState={saveState} variant={variant} onSave={saveWinner} onRestart={restart} /> : null}
        </div>
      </div>

      <div className={styles.prototypeState}>
        <span>Live state</span>
        <strong>{stage} · {actorIndex === 0 ? "person 1" : "person 2"} · {savedVotes}/4 reactions</strong>
      </div>
    </section>
  );
}

function SetupScreen({ busy, variant, onStart }: { busy: boolean; variant: VariantKey; onStart: () => void }) {
  return (
    <div className={`${styles.setupScreen} ${busy ? styles.setupBusy : ""}`}>
      <div className={styles.posterFan} aria-hidden="true">
        <img src={candidates[1].poster} alt="" />
        <img src={candidates[0].poster} alt="" />
        <img src="/concept-edge-of-tomorrow-poster.svg" alt="" />
      </div>
      <div className={styles.setupCopy}>
        <p>Saturday night · two private ballots</p>
        <h1>Find the movie you both actually want.</h1>
        <span>Six quick choices, one private handoff, no debate required.</span>
      </div>
      <div className={styles.setupSummary}>
        <span><b>C</b>Cezary + Sophie</span>
        <span>Under 2h 15m</span>
      </div>
      <button type="button" className={`${styles.primaryButton} ${busy ? styles.buttonBusy : ""}`} disabled={busy} onClick={onStart}>
        {busy ? <><BusyIcon variant={variant} /><span>Opening movie night</span><small>Preparing</small></> : <><span>Start tonight</span><strong>→</strong></>}
      </button>
    </div>
  );
}

function WaitScreen({ stage, step, variant }: { stage: "building" | "sealing" | "matching"; step: number; variant: VariantKey }) {
  const content = {
    building: {
      title: "Building your shortlist",
      labels: ["Reading tonight's mood", "Balancing both taste profiles", "Shortlist ready"],
    },
    sealing: {
      title: "Cezary's picks are private",
      labels: ["Saving reactions", "Removing vote clues", "Ready for handoff"],
    },
    matching: {
      title: "Finding the overlap",
      labels: ["Sealing Sophie's reactions", "Ruling out hard noes", "Resolving the strongest match"],
    },
  }[stage];
  const percent = [28, 64, 100][step] ?? 28;

  return (
    <div className={`${styles.waitScreen} ${styles[`wait_${stage}`]}`}>
      <WaitVisual variant={variant} step={step} stage={stage} />
      <div className={styles.waitCopy}>
        <p>{stage === "matching" ? "Two sealed ballots" : stage === "sealing" ? "Ballot complete" : "WatchSignal is working"}</p>
        <h1>{content.title}</h1>
        <span aria-live="polite">{content.labels[step]}</span>
      </div>
      <div className={styles.waitProgress} aria-label={`${percent}% complete`}>
        <div><span style={{ width: `${percent}%` }} /></div>
        <strong>{percent}%</strong>
      </div>
      <div className={styles.waitChecklist}>
        {content.labels.map((label, index) => (
          <div key={label} className={index < step ? styles.waitDone : index === step ? styles.waitActive : ""}>
            <i>{index < step ? "✓" : index + 1}</i>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function WaitVisual({ variant, step, stage }: { variant: VariantKey; step: number; stage: string }) {
  if (variant === "A") {
    return <div className={styles.preciseRing} style={{ "--progress": `${[100, 230, 355][step]}deg` } as CSSProperties}><span>{step + 1}</span></div>;
  }

  if (variant === "B") {
    return (
      <div className={styles.cinemaLoader} data-stage={stage}>
        <img src={candidates[1].poster} alt="" />
        <img src={candidates[0].poster} alt="" />
        <img src="/concept-edge-of-tomorrow-poster.svg" alt="" />
        <div className={styles.scanner} />
      </div>
    );
  }

  return (
    <div className={styles.signalLoader} aria-hidden="true">
      <i /><i /><i /><i /><i />
      <strong>{step === 2 ? "✓" : "W"}</strong>
    </div>
  );
}

function ReactionScreen({
  actor,
  actorIndex,
  candidate,
  movieIndex,
  pending,
  savedVotes,
  seenSaved,
  onSeen,
  onReact,
}: {
  actor: string;
  actorIndex: number;
  candidate: Candidate;
  movieIndex: number;
  pending: Reaction | null;
  savedVotes: number;
  seenSaved: boolean;
  onSeen: () => void;
  onReact: (reaction: Reaction) => void;
}) {
  return (
    <div className={styles.reactionScreen}>
      <div className={styles.reactionHeader}>
        <div><span>{actor}'s private picks</span><strong>{movieIndex + 1} of {candidates.length}</strong></div>
        <div className={styles.miniProgress}><span style={{ width: `${((movieIndex + 1) / candidates.length) * 100}%` }} /></div>
      </div>

      <article className={`${styles.movieCard} ${pending ? styles.cardCommitted : ""}`} data-reaction={pending ?? "idle"}>
        <img src={candidate.poster} alt="" />
        <div className={styles.posterShade} />
        <div className={styles.movieScore}><span>{candidate.score}</span> critic</div>
        <div className={styles.movieCopy}>
          <p>{candidate.year} · {candidate.runtime}</p>
          <h1>{candidate.title}</h1>
          <span>{candidate.tone}</span>
          <strong>{candidate.reason}</strong>
        </div>
        {pending ? <div className={styles.cardReceipt}><i>✓</i><span>{reactionLabels[pending]} saved privately</span></div> : null}
      </article>

      <button type="button" className={`${styles.seenButton} ${seenSaved ? styles.seenActive : ""}`} onClick={onSeen} disabled={Boolean(pending)}>
        <span>{seenSaved ? "✓" : "+"}</span>{seenSaved ? "Seen status saved" : "Also seen this"}
      </button>

      <div className={styles.reactionActions} aria-label="Tonight fit">
        {(["no", "maybe", "interested"] as Reaction[]).map((reaction) => {
          const selected = pending === reaction;
          return (
            <button
              type="button"
              key={reaction}
              className={selected ? styles.reactionSelected : ""}
              disabled={Boolean(pending)}
              onClick={() => onReact(reaction)}
            >
              <i>{selected ? "✓" : reaction === "no" ? "×" : reaction === "maybe" ? "◇" : "♥"}</i>
              <span>{selected ? "Saved" : reactionLabels[reaction]}</span>
              {selected ? <small>Private</small> : null}
            </button>
          );
        })}
      </div>
      <span className={styles.savedCounter}>{savedVotes + (actorIndex === 0 ? 0 : 0)} reactions sealed so far</span>
    </div>
  );
}

function HandoffScreen({ busy, variant, onUnlock }: { busy: boolean; variant: VariantKey; onUnlock: () => void }) {
  return (
    <div className={`${styles.handoffScreen} ${busy ? styles.handoffUnlocking : ""}`}>
      <div className={styles.privacyCurtain} aria-hidden="true"><i /><i /></div>
      <div className={styles.sealedStack} aria-hidden="true">
        <span /><span /><span />
        <strong>W</strong>
        <i>✓</i>
      </div>
      <div className={styles.handoffCopy}>
        <p>Cezary's ballot is sealed</p>
        <h1>Pass the phone to Sophie.</h1>
        <span>Her choices start on a clean screen. No titles, reactions, or vote counts are visible.</span>
      </div>
      <div className={styles.privacyProof}>
        <span><i>✓</i> Votes hidden</span>
        <span><i>✓</i> Same shortlist</span>
      </div>
      <button type="button" className={`${styles.primaryButton} ${busy ? styles.buttonBusy : ""}`} disabled={busy} onClick={onUnlock}>
        {busy ? <><BusyIcon variant={variant} /><span>Opening Sophie's pass</span><small>Private</small></> : <><span>I'm Sophie - begin</span><strong>→</strong></>}
      </button>
    </div>
  );
}

function RevealScreen({ saveState, variant, onSave, onRestart }: { saveState: SaveState; variant: VariantKey; onSave: () => void; onRestart: () => void }) {
  return (
    <div className={styles.revealScreen}>
      <div className={styles.revealSignals} aria-hidden="true"><i /><i /><strong>92</strong></div>
      <p>Both ballots unlocked</p>
      <h1>Tonight, you found it.</h1>
      <article className={styles.winnerCard}>
        <img src={candidates[0].poster} alt="Arrival poster" />
        <div>
          <span>92% shared signal</span>
          <h2>Arrival</h2>
          <p>Cezary wanted momentum. Sophie kept the emotional mystery open. Neither of you blocked it.</p>
        </div>
      </article>
      <div className={styles.revealActions}>
        <button type="button" className={`${styles.primaryButton} ${saveState !== "idle" ? styles.buttonBusy : ""} ${saveState === "saved" ? styles.buttonSuccess : ""}`} disabled={saveState !== "idle"} onClick={onSave}>
          {saveState === "idle" ? <><span>Save for tonight</span><strong>＋</strong></> : null}
          {saveState === "saving" ? <><BusyIcon variant={variant} /><span>Saving your winner</span><small>Syncing</small></> : null}
          {saveState === "saved" ? <><i className={styles.successMark}>✓</i><span>Saved for tonight</span><small>Done</small></> : null}
        </button>
        <button type="button" className={styles.restartButton} onClick={onRestart}>Replay the full flow</button>
      </div>
    </div>
  );
}

function BusyIcon({ variant }: { variant: VariantKey }) {
  return <i className={styles.busyIcon} data-kind={variant}><span /><span /><span /></i>;
}

function stageProgress(stage: Stage) {
  return {
    setup: 8,
    building: 18,
    reaction: 42,
    sealing: 50,
    handoff: 58,
    matching: 82,
    reveal: 100,
  }[stage];
}
