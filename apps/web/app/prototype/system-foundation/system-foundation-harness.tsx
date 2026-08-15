"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { demoCandidateViewModels } from "../../pass-the-phone-helpers";
import type { RankedCandidate } from "../../pass-the-phone-model";
import { RankedResultStage } from "../../pass-the-phone/results/ranked-result-stage";
import { WatchSignalIcon } from "../../ui/watchsignal-icons";
import {
  WatchSignalButton,
  WatchSignalHeader,
  WatchSignalIconButton,
} from "../../ui/primitives";
import styles from "./system-foundation.module.css";

type PreviewSurface = "cinema" | "utility";

const founderReactions = {
  arrival: "interested",
  "knives-out": "interested",
  "the-grand-budapest-hotel": "maybe",
  "past-lives": "maybe",
  "edge-of-tomorrow": "interested",
} as const;

const wifeReactions = {
  arrival: "interested",
  "knives-out": "maybe",
  "the-grand-budapest-hotel": "maybe",
  "past-lives": "interested",
  "edge-of-tomorrow": "no",
} as const;

export function SystemFoundationHarness() {
  const [surface, setSurface] = useState<PreviewSurface>("cinema");

  return (
    <main className={styles.harness} data-foundation-harness>
      <nav className={styles.surfaceSwitch} aria-label="Foundation preview surface">
        <button type="button" aria-label="Cinema preview" title="Cinema preview" aria-pressed={surface === "cinema"} onClick={() => setSurface("cinema")}>C</button>
        <button type="button" aria-label="Utility preview" title="Utility preview" aria-pressed={surface === "utility"} onClick={() => setSurface("utility")}>U</button>
      </nav>
      {surface === "cinema" ? <CinemaExample /> : <UtilityExample />}
    </main>
  );
}

function CinemaExample() {
  const rankedCandidates = useMemo(
    () => canonicalCinemaCandidates(),
    [],
  );
  const [continuationOpen, setContinuationOpen] = useState(false);

  return (
    <RankedResultStage
      rankedCandidates={rankedCandidates}
      peopleMode="couple"
      founderReactions={founderReactions}
      wifeReactions={wifeReactions}
      sharedReasons={{
        arrival: "Both wanted thoughtful sci-fi, and this stays tense without going bleak.",
        "knives-out": "One strong yes and one maybe kept it near the top.",
        "the-grand-budapest-hotel": "Both maybes made this the lighter backup.",
        "past-lives": "One strong yes and one maybe kept it in the shared five.",
        "edge-of-tomorrow": "One strong yes could not fully offset the other no.",
      }}
      continuationOpen={continuationOpen}
      continuationContent={<PreviewContinuation />}
      utilityContent={<PreviewUtilityOptions />}
      onToggleContinuation={() => setContinuationOpen((current) => !current)}
      onPosterFallback={(event) => { event.currentTarget.style.visibility = "hidden"; }}
    />
  );
}

function UtilityExample() {
  const [sheet, setSheet] = useState<"language" | null>(null);
  const [language, setLanguage] = useState("English audio & subtitles");
  const [intent, setIntent] = useState("thoughtful and tense, without going bleak");
  const [saved, setSaved] = useState(false);
  const languageButtonRef = useRef<HTMLButtonElement>(null);
  const languageDialogRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (sheet === null) {
      return;
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeSheet();
      }
    }

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [sheet]);

  function closeSheet() {
    setSheet(null);
    window.requestAnimationFrame(() => languageButtonRef.current?.focus());
  }

  function trapDialogFocus(event: ReactKeyboardEvent<HTMLElement>) {
    if (event.key !== "Tab") {
      return;
    }

    const dialog = languageDialogRef.current;
    if (!dialog) {
      return;
    }

    const focusable = Array.from(
      dialog.querySelectorAll<HTMLElement>(
        "button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])",
      ),
    ).filter((element) => !element.hasAttribute("hidden"));
    const first = focusable[0];
    const last = focusable.at(-1);
    if (!first || !last) {
      return;
    }

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaved(true);
  }

  return (
    <section className={styles.utilityScreen} aria-labelledby="utility-title">
      <WatchSignalHeader className={styles.utilityHeader}>
        <span className={styles.utilityStep}>Tonight</span>
      </WatchSignalHeader>
      <form className={styles.utilityForm} onSubmit={submit}>
        <header className={styles.utilityIntro}>
          <span>Movie night</span>
          <h1 id="utility-title">Ready when you are.</h1>
          <p>Check the essentials, then start.</p>
        </header>

        <div className={styles.settingRows}>
          <button type="button"><span><WatchSignalIcon name="users" />People</span><strong>Husband + Wife</strong><WatchSignalIcon name="chevron-right" /></button>
          <button ref={languageButtonRef} type="button" onClick={() => setSheet("language")}><span><WatchSignalIcon name="message" />Language</span><strong>{language}</strong><WatchSignalIcon name="chevron-right" /></button>
          <button type="button"><span><WatchSignalIcon name="play" />Availability</span><strong>Prime Video · Germany</strong><WatchSignalIcon name="chevron-right" /></button>
        </div>

        <label className={styles.intentField}>
          <span>What are you in the mood for?</span>
          <textarea value={intent} onChange={(event) => { setIntent(event.target.value); setSaved(false); }} rows={3} />
          <small>Optional. This guides tonight, not your lasting taste.</small>
        </label>

        <WatchSignalButton type="submit"><WatchSignalIcon name="sparkles" />Start movie night</WatchSignalButton>
        <p className={styles.formStatus} role="status">{saved ? "Ready. Your tonight signal is set." : "Your private picks come next."}</p>
      </form>

      {sheet === "language" ? (
        <div className={styles.utilitySheetLayer}>
          <button className={styles.utilityBackdrop} type="button" onClick={closeSheet} aria-label="Close language settings" />
          <section ref={languageDialogRef} className={styles.utilitySheet} role="dialog" aria-modal="true" aria-labelledby="language-sheet-title" onKeyDown={trapDialogFocus}>
            <header>
              <span aria-hidden="true" />
              <div><small>Tonight</small><h2 id="language-sheet-title">Language</h2></div>
              <WatchSignalIconButton label="Close language settings" onClick={closeSheet} autoFocus><WatchSignalIcon name="close" /></WatchSignalIconButton>
            </header>
            <div className={styles.languageOptions}>
              {["English audio & subtitles", "Subtitles are fine", "No preference"].map((option) => (
                <button key={option} type="button" aria-pressed={language === option} onClick={() => { setLanguage(option); closeSheet(); setSaved(false); }}>
                  <span>{option}</span>{language === option ? <WatchSignalIcon name="check" /> : null}
                </button>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}

function canonicalCinemaCandidates(): RankedCandidate[] {
  const canonical = [
    ["arrival", 84],
    ["knives-out", 72],
    ["the-grand-budapest-hotel", 61],
    ["past-lives", 52],
    ["edge-of-tomorrow", 38],
  ] as const;

  return canonical.map(([id, score], index) => {
    const candidate = demoCandidateViewModels.find((item) => item.id === id);
    if (!candidate) {
      throw new Error(`Missing canonical foundation candidate: ${id}`);
    }

    return {
      ...candidate,
      score,
      profileScore: score,
      matchIndex: {
        scoreKind: "match_index_v1",
        score,
        exactScore: score,
        baseSignal: score / 100,
        reactionDeltaRaw: 0,
        combinedRaw: score / 100,
        rawMinimum: -0.36,
        rawMaximum: 1.24,
      },
      baseRank: index + 1,
    };
  });
}

function PreviewContinuation() {
  return (
    <section className={styles.previewMessage}>
      <h2>Keep the same direction?</h2>
      <p>The real result reuses the existing five-more refinement here.</p>
      <WatchSignalButton><WatchSignalIcon name="refresh" />Find five more</WatchSignalButton>
    </section>
  );
}

function PreviewUtilityOptions() {
  return (
    <section className={styles.previewMessage}>
      <h2>Tonight’s result</h2>
      <p>Secondary result tools live here without competing with the movie.</p>
      <WatchSignalButton variant="secondary"><WatchSignalIcon name="bookmark" />Save to watchlist</WatchSignalButton>
    </section>
  );
}
