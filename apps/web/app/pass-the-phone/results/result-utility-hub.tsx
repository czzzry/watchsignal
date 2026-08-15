"use client";

import type { ReactNode } from "react";
import { WatchSignalIcon } from "../../ui/watchsignal-icons";
import styles from "./result-utility-hub.module.css";

export type ResultUtilityView = "home" | "watchlist" | "outcome";

export function ResultUtilityHub({ view, winnerTitle, saved, saveBusy, saveMessage, canSave, watchlistCount, children, onView, onToggleSave, onReset }: {
  view: ResultUtilityView;
  winnerTitle: string;
  saved: boolean;
  saveBusy: boolean;
  saveMessage: string | null;
  canSave: boolean;
  watchlistCount: number;
  children?: ReactNode;
  onView: (view: ResultUtilityView) => void;
  onToggleSave: () => void | Promise<void>;
  onReset: () => void;
}) {
  if (view !== "home") return <>{children}</>;
  return <section className={styles.home} aria-labelledby="result-options-title">
    <header><span>Tonight</span><h2 id="result-options-title">Keep the night moving</h2></header>
    <button className={styles.save} type="button" disabled={saveBusy || !canSave} onClick={() => void onToggleSave()}><span><WatchSignalIcon name={saved ? "check" : "bookmark"} /></span><div><strong>{saveBusy ? "Saving…" : saved ? "Saved" : `Save ${winnerTitle}`}</strong><small>{saved ? "Tap to undo" : "Shared watchlist"}</small></div></button>
    {saveMessage ? <p role={/couldn|need/i.test(saveMessage) ? "alert" : "status"}>{saveMessage}</p> : !canSave ? <p role="status">Shared watchlist needs a connection.</p> : null}
    <div className={styles.rows}>
      <button type="button" onClick={() => onView("watchlist")}><span><WatchSignalIcon name="bookmark" /></span><div><strong>Watchlist</strong><small>{watchlistCount === 0 ? "Nothing saved yet" : `${watchlistCount} saved`}</small></div><WatchSignalIcon name="chevron-right" /></button>
      <button type="button" onClick={() => onView("outcome")}><span><WatchSignalIcon name="check" /></span><div><strong>After tonight</strong><small>Save what you watched</small></div><WatchSignalIcon name="chevron-right" /></button>
    </div>
    <button className={styles.reset} type="button" onClick={onReset}>Start new night</button>
  </section>;
}
