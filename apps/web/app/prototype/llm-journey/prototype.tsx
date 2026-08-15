"use client";

// Three connected artifacts: the approved result reference, tonight intent, and five-more steering.

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { GoldenResult } from "./golden-result";
import styles from "./prototype.module.css";

type VariantKey = "A" | "B" | "C";
type IntentState = "compose" | "clarify" | "confirm" | "ready";

const variants: VariantKey[] = ["A", "B", "C"];
const variantNames: Record<VariantKey, string> = {
  A: "Golden target · result",
  B: "Revised · tonight",
  C: "Revised · five more",
};

const posterUrls = [
  "https://image.tmdb.org/t/p/w780/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
  "https://image.tmdb.org/t/p/w342/pThyQovXQrw2m0s9x82twj48Jq4.jpg",
  "https://image.tmdb.org/t/p/w342/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg",
  "https://image.tmdb.org/t/p/w342/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg",
  "https://image.tmdb.org/t/p/w342/uUHvlkLavotfGsNtosDy8ShsIYF.jpg",
];

const newPosterUrls = [
  "https://image.tmdb.org/t/p/w342/yf5IuMW6GHghu39kxA0oFx7Bxmj.jpg",
  "https://image.tmdb.org/t/p/w342/clq4So9spa9cXk3MZy2iMdqkxP2.jpg",
  "https://image.tmdb.org/t/p/w342/hkmz9rxgcweizXNElozGeKwmAJE.jpg",
  "https://image.tmdb.org/t/p/w342/85R8LMyn9f2Lev2YPBF8Nughrkv.jpg",
  "https://image.tmdb.org/t/p/w342/v31MsWhF9WFh7Qooq6xSBbmJxoG.jpg",
];

const originalScores = [84, 72, 61, 52, 38];

export function LlmJourneyPrototype() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requested = searchParams.get("variant")?.toUpperCase();
  const variant: VariantKey = variants.includes(requested as VariantKey) ? requested as VariantKey : "A";

  function chooseVariant(next: VariantKey) {
    router.replace(`/prototype/llm-journey?variant=${next}`, { scroll: false });
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
      <div className={styles.prototypeNotice}>Connected flow · illustrative only</div>
      <div className={styles.phoneFrame}>
        {variant === "A" ? <GoldenResult onFiveMore={() => chooseVariant("C")} /> : null}
        {variant === "B" ? <TonightIntentArtifact /> : null}
        {variant === "C" ? <FiveMoreArtifact /> : null}
      </div>
      <PrototypeSwitcher current={variant} onChange={chooseVariant} />
    </main>
  );
}

function TonightIntentArtifact() {
  const [text, setText] = useState("Funny and clever, but not bleak. Under two hours.");
  const [state, setState] = useState<IntentState>("compose");
  const [clarification, setClarification] = useState<string | null>(null);
  const [tokens, setTokens] = useState(["Funny", "Clever", "Not bleak", "Under 2h"]);

  const interpretedTokens = useMemo(() => parseIntent(text, clarification), [text, clarification]);

  function interpret(event?: FormEvent) {
    event?.preventDefault();
    if (!text.trim()) return;
    if (/\bsad\b/i.test(text) && !/comfort|match|lean into|stay with/i.test(text)) {
      setState("clarify");
      return;
    }
    setTokens(interpretedTokens);
    setState("confirm");
  }

  function answerClarification(answer: string) {
    setClarification(answer);
    setTokens(parseIntent(text, answer));
    setState("confirm");
  }

  function removeToken(token: string) {
    setTokens((current) => current.filter((item) => item !== token));
  }

  return (
    <section className={`${styles.screen} ${styles.intentScreen}`}>
      <PosterConstellation posters={posterUrls.slice(0, 3)} />
      <div className={styles.intentAtmosphere} />
      <AppHeader trailing="Tonight" />

      <div className={styles.intentBody}>
        <div className={styles.sessionLine}>
          <span>Cezary + Sophie</span>
          <i aria-hidden="true" />
          <span>Prime Video</span>
          <button type="button">Edit</button>
        </div>

        {state === "compose" ? (
          <>
            <h1>What feels right tonight?</h1>
            <form className={styles.intentComposer} onSubmit={interpret}>
              <label htmlFor="tonight-intent">Say it naturally</label>
              <textarea id="tonight-intent" value={text} onChange={(event) => setText(event.target.value)} rows={3} />
              <div className={styles.composerActions}>
                <span>Try “I feel sad”</span>
                <button type="submit" aria-label="Interpret what feels right"><ArrowIcon /></button>
              </div>
            </form>
            <p className={styles.privacyLine}><MoonIcon />Only for tonight</p>
          </>
        ) : null}

        {state === "clarify" ? (
          <div className={styles.clarifyPanel}>
            <SignalMark />
            <p>I understand how you feel.</p>
            <h1>What would help tonight?</h1>
            <div className={styles.clarifyChoices}>
              <button type="button" onClick={() => answerClarification("Comforting")}>Lift me up<SunIcon /></button>
              <button type="button" onClick={() => answerClarification("Match the feeling")}>Stay with it<MoonIcon /></button>
            </div>
            <button className={styles.quietAction} type="button" onClick={() => setState("compose")}>Back</button>
          </div>
        ) : null}

        {state === "confirm" || state === "ready" ? (
          <div className={styles.confirmPanel}>
            <SignalMark ready={state === "ready"} />
            <p>{state === "ready" ? "Locked in for tonight" : "Here’s what I heard"}</p>
            <h1>{state === "ready" ? "Your five will follow this feeling." : "Light, sharp, never heavy."}</h1>
            <div className={styles.signalTokens} aria-label="Interpreted mood">
              {tokens.map((token) => (
                <button key={token} type="button" onClick={() => removeToken(token)} aria-label={`Remove ${token}`}>
                  {token}<span aria-hidden="true">×</span>
                </button>
              ))}
            </div>
            {state === "confirm" ? (
              <>
                <button className={styles.primaryAction} type="button" onClick={() => setState("ready")}>That’s right<ArrowIcon /></button>
                <button className={styles.quietAction} type="button" onClick={() => setState("compose")}>Change my words</button>
              </>
            ) : (
              <button className={styles.primaryAction} type="button">Start Cezary’s pass<ArrowIcon /></button>
            )}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function FiveMoreArtifact() {
  const [text, setText] = useState("Lighter and faster. No superheroes.");
  const [state, setState] = useState<"compose" | "confirm" | "finding" | "ready">("compose");
  const [tokens, setTokens] = useState(["Lighter", "Faster", "No superheroes"]);

  function interpret(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    setTokens(parseIntent(text));
    setState("confirm");
  }

  function findFive() {
    setState("finding");
    window.setTimeout(() => setState("ready"), 850);
  }

  return (
    <section className={`${styles.screen} ${styles.moreScreen}`}>
      <div className={styles.moreGlow} />
      <AppHeader trailing="Five more" />

      <div className={styles.moreBody}>
        <div className={styles.oldBatch} aria-label="Previous ranked picks">
          {posterUrls.map((poster, index) => (
            <span key={poster} className={index === 0 ? styles.oldBatchLead : ""}>
              <img src={poster} alt="" />
              <b>{originalScores[index]}</b>
            </span>
          ))}
        </div>

        {state === "ready" ? (
          <div className={styles.newBatchState}>
            <p>Second wave</p>
            <h1>Five lighter options.</h1>
            <div className={styles.newBatchPosters}>
              {newPosterUrls.map((poster, index) => <img key={poster} src={poster} alt="" data-position={index} />)}
            </div>
            <div className={styles.signalTokens}>
              {tokens.map((token) => <span key={token}>{token}</span>)}
            </div>
            <button className={styles.primaryAction} type="button">Open the new five<ArrowIcon /></button>
          </div>
        ) : (
          <>
            <div className={styles.moreHeading}>
              <p>Nothing won you over?</p>
              <h1>Change the signal.</h1>
            </div>

            {state === "compose" ? (
              <>
                <div className={styles.quickSteers}>
                  {["Lighter", "Faster", "Different"].map((value) => (
                    <button key={value} type="button" onClick={() => setText(value)}>{value}</button>
                  ))}
                </div>
                <form className={styles.moreComposer} onSubmit={interpret}>
                  <label htmlFor="more-intent">Or say what should change</label>
                  <div>
                    <input id="more-intent" value={text} onChange={(event) => setText(event.target.value)} />
                    <button type="submit" aria-label="Interpret this direction"><ArrowIcon /></button>
                  </div>
                </form>
                <p className={styles.preservedLine}><CheckIcon />Your reactions stay. No repeats.</p>
              </>
            ) : null}

            {state === "confirm" || state === "finding" ? (
              <div className={styles.steerConfirmation}>
                <div className={styles.steerReadback}><SignalMark /><span><small>Now looking for</small><strong>Lighter, faster, no superhero films.</strong></span></div>
                <div className={styles.signalTokens}>
                  {tokens.map((token) => <span key={token}>{token}</span>)}
                </div>
                <button className={styles.primaryAction} type="button" onClick={findFive} disabled={state === "finding"}>
                  {state === "finding" ? <><LoadingMark />Finding your five</> : <>Use this direction<ArrowIcon /></>}
                </button>
                {state === "confirm" ? <button className={styles.quietAction} type="button" onClick={() => setState("compose")}>Change it</button> : null}
              </div>
            ) : null}
          </>
        )}
      </div>
    </section>
  );
}

function parseIntent(text: string, clarification?: string | null) {
  const normalized = `${text} ${clarification ?? ""}`.toLowerCase();
  const tokens: string[] = [];
  if (/funny|comedy|humor/.test(normalized)) tokens.push("Funny");
  if (/clever|smart|sharp/.test(normalized)) tokens.push("Clever");
  if (/not bleak|no bleak|light|lighter|comfort/.test(normalized)) tokens.push(clarification === "Comforting" ? "Comforting" : "Lighter");
  if (/under two|under 2|short|faster|quick/.test(normalized)) tokens.push(/faster|quick/.test(normalized) ? "Faster" : "Under 2h");
  if (/no super|not super|avoid super/.test(normalized)) tokens.push("No superheroes");
  if (/match the feeling|stay with/.test(normalized)) tokens.push("Match my mood");
  return [...new Set(tokens.length ? tokens : ["Open direction"])];
}

function PosterConstellation({ posters }: { posters: string[] }) {
  return (
    <div className={styles.posterConstellation} aria-hidden="true">
      {posters.map((poster, index) => <img key={poster} src={poster} alt="" data-position={index} />)}
      <span className={styles.signalArc} />
    </div>
  );
}

function AppHeader({ trailing }: { trailing: string }) {
  return (
    <header className={styles.appHeader}>
      <div className={styles.brand}><span>W</span><strong>WatchSignal</strong></div>
      <p>{trailing}</p>
    </header>
  );
}

function SignalMark({ ready = false }: { ready?: boolean }) {
  return <span className={`${styles.signalMark} ${ready ? styles.signalMarkReady : ""}`}><SparkIcon /></span>;
}

function PrototypeSwitcher({ current, onChange }: { current: VariantKey; onChange: (variant: VariantKey) => void }) {
  const currentIndex = variants.indexOf(current);
  return (
    <nav className={styles.switcher} aria-label="LLM journey prototype variants">
      <button type="button" onClick={() => onChange(variants[(currentIndex + variants.length - 1) % variants.length])} aria-label="Previous artifact">←</button>
      <div><span>{current === "A" ? "Gauntlet candidate" : "New artifact"}</span><strong>{variantNames[current]}</strong></div>
      <button type="button" onClick={() => onChange(variants[(currentIndex + 1) % variants.length])} aria-label="Next artifact">→</button>
    </nav>
  );
}

function ArrowIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>; }
function SparkIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5c.7 4.3 2.4 6 6.5 6.7-4.1.7-5.8 2.4-6.5 6.8-.7-4.4-2.4-6.1-6.5-6.8C9.6 9.5 11.3 7.8 12 3.5Z" /><path d="M18.3 15.3c.3 1.8 1 2.5 2.7 2.8-1.7.3-2.4 1-2.7 2.8-.3-1.8-1-2.5-2.7-2.8 1.7-.3 2.4-1 2.7-2.8Z" /></svg>; }
function MoonIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 15.4A8 8 0 0 1 8.6 4a8 8 0 1 0 11.4 11.4Z" /></svg>; }
function SunIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3.5" /><path d="M12 2.5v2M12 19.5v2M4.5 4.5l1.4 1.4M18.1 18.1l1.4 1.4M2.5 12h2M19.5 12h2M4.5 19.5l1.4-1.4M18.1 5.9l1.4-1.4" /></svg>; }
function CheckIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4 10-10" /></svg>; }
function LoadingMark() { return <span className={styles.loadingMark} aria-hidden="true" />; }
