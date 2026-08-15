"use client";

// Three approval artifacts showing how the Afterglow direction scales across the real core flow.

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import styles from "./prototype.module.css";

type ScreenKey = "setup" | "reaction" | "handoff";
type SettingKey = "people" | "language" | "availability" | "mode" | "mood";
type Reaction = "interested" | "maybe" | "no";

const posters = [
  "https://image.tmdb.org/t/p/w780/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
  "https://image.tmdb.org/t/p/w342/pThyQovXQrw2m0s9x82twj48Jq4.jpg",
  "https://image.tmdb.org/t/p/w342/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg",
  "https://image.tmdb.org/t/p/w342/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg",
  "https://image.tmdb.org/t/p/w342/uUHvlkLavotfGsNtosDy8ShsIYF.jpg",
];

const screenNames: Record<ScreenKey, string> = {
  setup: "Tonight",
  reaction: "Private pick",
  handoff: "Handoff",
};

export function NorthStarFlowPrototype() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requested = searchParams.get("screen")?.toLowerCase();
  const screen: ScreenKey = requested === "reaction" || requested === "handoff" ? requested : "setup";

  function chooseScreen(next: ScreenKey) {
    router.replace(`/prototype/north-star-flow?screen=${next}`, { scroll: false });
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.matches("input, textarea, [contenteditable='true']")) return;
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      const order: ScreenKey[] = ["setup", "reaction", "handoff"];
      const index = order.indexOf(screen);
      const offset = event.key === "ArrowRight" ? 1 : -1;
      chooseScreen(order[(index + offset + order.length) % order.length]);
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [screen]);

  return (
    <main className={styles.studio}>
      <div className={styles.prototypeNotice}>Afterglow flow prototype · nothing is saved</div>
      <div className={styles.phoneFrame}>
        {screen === "setup" ? <SetupArtifact /> : null}
        {screen === "reaction" ? <ReactionArtifact /> : null}
        {screen === "handoff" ? <HandoffArtifact /> : null}
      </div>
      <ScreenSwitcher current={screen} onChange={chooseScreen} />
    </main>
  );
}

function SetupArtifact() {
  const [expanded, setExpanded] = useState<SettingKey | null>(null);
  const [people, setPeople] = useState("Cezary + Sophie");
  const [language, setLanguage] = useState("English");
  const [availability, setAvailability] = useState("Prime Video");
  const [mode, setMode] = useState("Compromise");
  const [mood, setMood] = useState("Thoughtful, not bleak");
  const [starting, setStarting] = useState(false);
  const isTogether = people === "Cezary + Sophie";
  const firstActor = people === "Sophie" ? "Sophie" : "Cezary";

  return (
    <section className={`${styles.screen} ${styles.setupScreen}`}>
      <div className={styles.setupBackdrop}>
        {posters.slice(0, 3).map((poster, index) => <img key={poster} src={poster} alt="" data-position={index} />)}
      </div>
      <div className={styles.setupAtmosphere} />
      <AppHeader trailing="Tonight" />

      <div className={styles.setupContent}>
        <p className={styles.screenCue}>Tuesday · Movie night</p>
        <h1 className={styles.cinematicTitle}>{isTogether ? "Tonight, we pick together." : "Tonight, you pick."}</h1>

        <div className={styles.settingBoard}>
          <SettingRow label="People" value={people} open={expanded === "people"} onToggle={() => setExpanded(expanded === "people" ? null : "people")}>
            <ChoiceChips values={["Cezary + Sophie", "Cezary", "Sophie"]} current={people} onChoose={(value) => { setPeople(value); setExpanded(null); }} />
          </SettingRow>
          <SettingRow label="Language" value={language} open={expanded === "language"} onToggle={() => setExpanded(expanded === "language" ? null : "language")}>
            <ChoiceChips values={["English", "Subtitles OK", "No rules"]} current={language} onChoose={(value) => { setLanguage(value); setExpanded(null); }} />
          </SettingRow>
          <SettingRow label="Watch on" value={availability} open={expanded === "availability"} onToggle={() => setExpanded(expanded === "availability" ? null : "availability")}>
            <ChoiceChips values={["Prime Video", "Any streaming"]} current={availability} onChoose={(value) => { setAvailability(value); setExpanded(null); }} />
          </SettingRow>
          {isTogether ? (
            <SettingRow label="Mode" value={mode} open={expanded === "mode"} onToggle={() => setExpanded(expanded === "mode" ? null : "mode")}>
              <ChoiceChips values={["Compromise", "Cezary first", "Sophie first"]} current={mode} onChoose={(value) => { setMode(value); setExpanded(null); }} />
            </SettingRow>
          ) : null}
          <SettingRow label="Mood" value={mood || "Open to anything"} open={expanded === "mood"} onToggle={() => setExpanded(expanded === "mood" ? null : "mood")}>
            <div className={styles.moodEditor}>
              <input value={mood} onChange={(event) => setMood(event.target.value)} placeholder="Funny, short, not bleak..." />
              <button type="button" onClick={() => setExpanded(null)}>Done</button>
            </div>
          </SettingRow>
        </div>

        <button className={styles.primaryAction} type="button" onClick={() => setStarting(true)} disabled={starting}>
          {starting ? <><LoadingMark />Building your five</> : <>Start {firstActor}&apos;s pass<ChevronIcon /></>}
        </button>
        <p className={styles.microcopy}>{isTogether ? "Five each · Private until the reveal" : "Five picks · Just for you"}</p>
      </div>
    </section>
  );
}

function SettingRow({ label, value, open, onToggle, children }: { label: string; value: string; open: boolean; onToggle: () => void; children: ReactNode }) {
  return (
    <div className={styles.settingRow}>
      <button type="button" onClick={onToggle} aria-expanded={open}>
        <span>{label}</span><strong>{value}</strong><ChevronIcon down={open} />
      </button>
      {open ? <div className={styles.settingOptions}>{children}</div> : null}
    </div>
  );
}

function ChoiceChips({ values, current, onChoose }: { values: string[]; current: string; onChoose: (value: string) => void }) {
  return (
    <div className={styles.choiceChips}>
      {values.map((value) => <button key={value} className={value === current ? styles.choiceChipActive : ""} type="button" onClick={() => onChoose(value)}>{value}</button>)}
    </div>
  );
}

function ReactionArtifact() {
  const [reaction, setReaction] = useState<Reaction | null>(null);
  const [layer, setLayer] = useState<"details" | "memory" | null>(null);
  const [memory, setMemory] = useState<string | null>(null);

  return (
    <section className={`${styles.screen} ${styles.reactionScreen}`}>
      <img className={styles.reactionPoster} src={posters[1]} alt="Knives Out movie poster" />
      <div className={styles.reactionAtmosphere} />

      <header className={styles.reactionHeader}>
        <button type="button" aria-label="Back"><BackIcon /></button>
        <div className={styles.progressRail}><i><b /></i><span>1 / 5</span></div>
        <span className={styles.privateMark}><LockIcon />Private</span>
      </header>

      <div className={styles.reactionContent}>
        <div className={styles.criticDial}><strong>97</strong><span>critics</span></div>
        <h1 className={styles.cinematicTitle}>Knives Out</h1>
        <p className={styles.movieMeta}>2019 · 2h 11m · Mystery · Comedy</p>
        <p className={styles.reactionReason}>A sharp mystery with momentum and a lighter edge.</p>
        {memory ? <p className={styles.memorySaved}><CheckIcon />Seen memory: {memory}</p> : null}

        <div className={styles.utilityActions}>
          <button type="button" onClick={() => setLayer("details")}><InfoIcon />More</button>
          <button type="button" onClick={() => setLayer("memory")}><EyeIcon />Seen before</button>
        </div>

        <div className={styles.reactionActions} role="group" aria-label="Tonight fit for Knives Out">
          <ReactionButton label="Interested" kind="interested" selected={reaction === "interested"} onClick={() => setReaction("interested")} />
          <ReactionButton label="Maybe" kind="maybe" selected={reaction === "maybe"} onClick={() => setReaction("maybe")} />
          <ReactionButton label="No" kind="no" selected={reaction === "no"} onClick={() => setReaction("no")} />
        </div>
        <p className={styles.microcopy}>{reaction ? `${reaction === "no" ? "No" : reaction[0].toUpperCase() + reaction.slice(1)} saved privately` : "Cezary, does this fit tonight?"}</p>
      </div>

      {layer === "details" ? <DetailsLayer onClose={() => setLayer(null)} /> : null}
      {layer === "memory" ? <MemoryLayer selected={memory} onChoose={(value) => { setMemory(value); setLayer(null); }} onClose={() => setLayer(null)} /> : null}
    </section>
  );
}

function ReactionButton({ label, kind, selected, onClick }: { label: string; kind: Reaction; selected: boolean; onClick: () => void }) {
  return (
    <button className={selected ? styles.reactionSelected : ""} type="button" onClick={onClick}>
      <span>{kind === "interested" ? <HeartIcon /> : kind === "maybe" ? <MaybeIcon /> : <NoIcon />}</span>
      <strong>{selected ? "Saved" : label}</strong>
    </button>
  );
}

function DetailsLayer({ onClose }: { onClose: () => void }) {
  return (
    <div className={styles.layer}>
      <button className={styles.layerBackdrop} type="button" aria-label="Close details" onClick={onClose} />
      <section className={styles.layerSheet} aria-label="Knives Out details">
        <span className={styles.sheetHandle} />
        <header><h2>Why tonight?</h2><button type="button" onClick={onClose} aria-label="Close">×</button></header>
        <p>A playful whodunit that moves quickly without becoming weightless.</p>
        <dl><div><dt>Cast</dt><dd>Daniel Craig · Ana de Armas</dd></div><div><dt>Audio</dt><dd>English</dd></div><div><dt>Watch</dt><dd>Available tonight</dd></div></dl>
        <button className={styles.sheetAction} type="button" onClick={onClose}>Done</button>
      </section>
    </div>
  );
}

function MemoryLayer({ selected, onChoose, onClose }: { selected: string | null; onChoose: (value: string) => void; onClose: () => void }) {
  return (
    <div className={styles.layer}>
      <button className={styles.layerBackdrop} type="button" aria-label="Close seen memory" onClick={onClose} />
      <section className={styles.layerSheet} aria-label="Save seen memory">
        <span className={styles.sheetHandle} />
        <header><h2>You&apos;ve seen it?</h2><button type="button" onClick={onClose} aria-label="Close">×</button></header>
        <p>This updates memory. You can still answer whether it fits tonight.</p>
        <div className={styles.memoryChoices}>
          {["Loved it", "It was fine", "Not for me", "I forget"].map((value) => <button key={value} className={selected === value ? styles.memoryChoiceActive : ""} type="button" onClick={() => onChoose(value)}>{value}<span>{selected === value ? "✓" : ""}</span></button>)}
        </div>
      </section>
    </div>
  );
}

function HandoffArtifact() {
  const [opening, setOpening] = useState(false);

  return (
    <section className={`${styles.screen} ${styles.handoffScreen}`}>
      <div className={styles.handoffGlow} />
      <header className={styles.handoffHeader}>
        <button type="button" aria-label="Back"><BackIcon /></button>
        <BrandMark compact />
        <span>2 / 3</span>
      </header>

      <div className={styles.handoffContent}>
        <div className={styles.handoffVisual} aria-hidden="true">
          <div className={styles.handoffCards}>{posters.slice(0, 5).map((poster) => <img key={poster} src={poster} alt="" />)}</div>
          <div className={styles.lockSeal}><LockIcon /></div>
        </div>

        <p className={styles.screenCue}>Cezary&apos;s pass is sealed</p>
        <h1 className={styles.cinematicTitle}>Pass to Sophie.</h1>
        <div className={styles.privacyProof}>
          <span><CheckIcon />Same five movies</span>
          <span><CheckIcon />Cezary&apos;s answers hidden</span>
        </div>

        <button className={styles.primaryAction} type="button" onClick={() => setOpening(true)} disabled={opening}>
          {opening ? <><LoadingMark />Opening Sophie&apos;s pass</> : <>I&apos;m Sophie<ChevronIcon /></>}
        </button>
        <p className={styles.microcopy}>The overlap appears only after both passes</p>
      </div>
    </section>
  );
}

function AppHeader({ trailing }: { trailing: string }) {
  return <header className={styles.appHeader}><BrandMark /><span>{trailing}</span></header>;
}

function BrandMark({ compact = false }: { compact?: boolean }) {
  return <div className={styles.brand}><span>W</span>{compact ? null : <strong>WatchSignal</strong>}</div>;
}

function ScreenSwitcher({ current, onChange }: { current: ScreenKey; onChange: (value: ScreenKey) => void }) {
  const order: ScreenKey[] = ["setup", "reaction", "handoff"];
  const index = order.indexOf(current);
  return (
    <nav className={styles.switcher} aria-label="Flow prototype screens">
      <button type="button" onClick={() => onChange(order[(index + 2) % 3])} aria-label="Previous screen">←</button>
      <div><span>Core flow</span><strong>{screenNames[current]}</strong></div>
      <button type="button" onClick={() => onChange(order[(index + 1) % 3])} aria-label="Next screen">→</button>
    </nav>
  );
}

function ChevronIcon({ down = false }: { down?: boolean }) {
  return <svg className={down ? styles.chevronDown : ""} viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>;
}
function BackIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>; }
function LockIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="3" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></svg>; }
function InfoIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8" /><path d="M12 11v5M12 8h.01" /></svg>; }
function EyeIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 12s3-5 8.5-5 8.5 5 8.5 5-3 5-8.5 5-8.5-5-8.5-5Z" /><circle cx="12" cy="12" r="2" /></svg>; }
function HeartIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20 4.8 13.4C1.2 10.1 3 5 7.4 5c2 0 3.6 1.1 4.6 2.6C13 6.1 14.6 5 16.6 5 21 5 22.8 10.1 19.2 13.4Z" /></svg>; }
function MaybeIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 19.5 3.8 15.7C1.2 13.2 2.3 9.6 5 8.6c1.8-.7 3.8.2 4.6 1.8.8-1.6 2.8-2.5 4.6-1.8 2.7 1 3.8 4.6 1.2 7.1L11.2 19.5" /><path d="M17.8 12.3 15.6 10c-1.5-1.5-.9-3.8.8-4.5 1.1-.4 2.3.1 2.8 1.1.5-1 1.7-1.5 2.8-1.1 1.7.7 2.3 3 .8 4.5l-2.2 2.3" /></svg>; }
function NoIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>; }
function CheckIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4 10-10" /></svg>; }
function LoadingMark() { return <span className={styles.loadingMark} aria-hidden="true" />; }
