"use client";

import { useEffect, useState } from "react";
import styles from "./redesign-gauntlet.module.css";

type AgentState = "working" | "judging" | "waiting" | "done";
type SliceState = "queued" | "in_progress" | "in_review" | "revising" | "accepted" | "blocked";

type GauntletStatus = {
  updatedAt: string;
  phase: string;
  summary: string;
  completed: number;
  total: number;
  activeAgents: Array<{ role: string; name: string; task: string; state: AgentState }>;
  slices: Array<{ id: string; name: string; status: SliceState; iteration: number; owner: string; judge: string }>;
  recent: string[];
  blockers: string[];
};

const emptyStatus: GauntletStatus = {
  updatedAt: "",
  phase: "Connecting",
  summary: "Loading the latest gauntlet state.",
  completed: 0,
  total: 8,
  activeAgents: [],
  slices: [],
  recent: [],
  blockers: [],
};

export function RedesignGauntletBoard() {
  const [status, setStatus] = useState<GauntletStatus>(emptyStatus);

  useEffect(() => {
    let active = true;
    async function refresh() {
      const response = await fetch(`/redesign-gauntlet-status.json?t=${Date.now()}`, { cache: "no-store" }).catch(() => null);
      if (!response?.ok) return;
      const payload = await response.json() as GauntletStatus;
      if (active) setStatus(payload);
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 4000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  const progress = status.total > 0 ? Math.round((status.completed / status.total) * 100) : 0;

  return (
    <main className={styles.board}>
      <header className={styles.header}>
        <div className={styles.brand}><span>W</span><strong>WatchSignal</strong></div>
        <a href="/prototype/llm-journey?variant=A">Golden bar</a>
      </header>

      <section className={styles.hero}>
        <div className={styles.phaseLine}><span className={styles.liveDot} />{status.phase}</div>
        <h1>Redesign gauntlet</h1>
        <p>{status.summary}</p>
        <div className={styles.progressMeta}><strong>{status.completed}/{status.total} slices accepted</strong><span>{progress}%</span></div>
        <div className={styles.progressTrack}><i style={{ transform: `scaleX(${progress / 100})` }} /></div>
      </section>

      <section className={styles.agentSection} aria-labelledby="agents-heading">
        <div className={styles.sectionHeading}><h2 id="agents-heading">Active team</h2><span>Updates automatically</span></div>
        <div className={styles.agentRail}>
          {status.activeAgents.map((agent) => (
            <article key={`${agent.role}-${agent.name}`}>
              <span className={`${styles.agentState} ${styles[`agent_${agent.state}`]}`} />
              <p>{agent.role}</p>
              <strong>{agent.name}</strong>
              <small>{agent.task}</small>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.sliceSection} aria-labelledby="slices-heading">
        <div className={styles.sectionHeading}><h2 id="slices-heading">Slices</h2><span>Build → judge → revise</span></div>
        <div className={styles.sliceList}>
          {status.slices.map((slice) => (
            <article key={slice.id} className={styles[`slice_${slice.status}`]}>
              <span className={styles.sliceId}>{slice.id}</span>
              <div><strong>{slice.name}</strong><small>{slice.owner} · {slice.judge}{slice.iteration > 0 ? ` · Round ${slice.iteration}` : ""}</small></div>
              <span className={styles.statusLabel}>{statusLabel(slice.status)}</span>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.logSection} aria-labelledby="log-heading">
        <div className={styles.sectionHeading}><h2 id="log-heading">Latest</h2><time>{formatTime(status.updatedAt)}</time></div>
        <ol>{status.recent.map((entry) => <li key={entry}>{entry}</li>)}</ol>
        {status.blockers.length > 0 ? <div className={styles.blockers}><strong>Blocked</strong>{status.blockers.map((item) => <p key={item}>{item}</p>)}</div> : null}
      </section>
    </main>
  );
}

function statusLabel(status: SliceState) {
  return ({ queued: "Queued", in_progress: "Building", in_review: "Judging", revising: "Revising", accepted: "Accepted", blocked: "Blocked" } as const)[status];
}

function formatTime(value: string) {
  if (!value) return "Waiting";
  return new Intl.DateTimeFormat("en", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}
