"use client";

import { useMemo, useState } from "react";
import type { SetupLoadResult } from "./setup-api";
import {
  demoCandidates,
  reactionLabels,
  type DemoCandidate,
  type ReactionValue,
  type SessionMode,
} from "./session-fixtures";
import {
  advanceSessionHandoff,
  createSharedSession,
  getSessionDebugHistory,
  loadRecommendationShortlist,
  submitSessionReactions,
  toApiSessionMode,
  type DebugHistoryReactionPayload,
  type DebugHistoryRecommendationCandidatePayload,
  type DebugHistorySessionPayload,
  type ShortlistCandidatePayload,
  type SharedSessionPayload,
} from "./session-client";

type ApiHealth = {
  connected: boolean;
  label: "Connected" | "Disconnected";
  detail: string;
};

type PassThePhoneWizardProps = {
  apiHealth: ApiHealth;
  setupLoad: SetupLoadResult;
};

type WizardStep = "setup" | "founder" | "handoff" | "wife" | "results";

type ReactionState = Record<string, ReactionValue | undefined>;

type SessionSource = "api" | "demo";

type SyncStatus = "ready" | "saving" | "loading";

type DebugHistoryStatus = "idle" | "loading" | "ready" | "failed";

const stepOrder: WizardStep[] = ["setup", "founder", "handoff", "wife", "results"];

const stepLabels: Record<WizardStep, string> = {
  setup: "Setup",
  founder: "First pass",
  handoff: "Handoff",
  wife: "Second pass",
  results: "Pick",
};

const sessionModeLabels: Record<SessionMode, string> = {
  compromise: "Compromise",
  "founder-first": "Founder first",
  "wife-first": "Wife first",
};

const fallbackPosterUrl =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 342 513'%3E%3Crect width='342' height='513' fill='%23e1eef2'/%3E%3Crect x='42' y='78' width='258' height='357' rx='18' fill='%23ffffff' stroke='%23245f73' stroke-width='8'/%3E%3Ccircle cx='126' cy='184' r='32' fill='%23245f73'/%3E%3Ccircle cx='216' cy='184' r='32' fill='%23245f73'/%3E%3Cpath d='M102 306h138' stroke='%23245f73' stroke-width='16' stroke-linecap='round'/%3E%3C/svg%3E";

export function PassThePhoneWizard({
  apiHealth,
  setupLoad,
}: PassThePhoneWizardProps) {
  const profiles = setupLoad.setup.profiles
    .slice()
    .sort((first, second) => first.order - second.order);
  const founderLabel = profiles[0]?.label || "Husband";
  const wifeLabel = profiles[1]?.label || "Wife";
  const [step, setStep] = useState<WizardStep>("setup");
  const [sessionMode, setSessionMode] = useState<SessionMode>("compromise");
  const [founderIndex, setFounderIndex] = useState(0);
  const [wifeIndex, setWifeIndex] = useState(0);
  const [sessionCandidates, setSessionCandidates] =
    useState<DemoCandidate[]>(demoCandidates);
  const [founderReactions, setFounderReactions] = useState<ReactionState>({});
  const [wifeReactions, setWifeReactions] = useState<ReactionState>({});
  const [sessionSource, setSessionSource] = useState<SessionSource>(
    apiHealth.connected ? "api" : "demo",
  );
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("ready");
  const [apiError, setApiError] = useState<string | null>(
    apiHealth.connected ? null : "API is disconnected, so this review is using demo data.",
  );
  const [sharedSession, setSharedSession] = useState<SharedSessionPayload | null>(
    null,
  );
  const [debugHistory, setDebugHistory] =
    useState<DebugHistorySessionPayload | null>(null);
  const [debugHistoryStatus, setDebugHistoryStatus] =
    useState<DebugHistoryStatus>("idle");
  const [debugHistoryMessage, setDebugHistoryMessage] = useState<string | null>(
    null,
  );
  const participantIds = [profiles[0]?.id || "husband", profiles[1]?.id || "wife"];

  const rankedCandidates = useMemo(
    () =>
      rankCandidates({
        sessionMode,
        candidates: sessionCandidates,
        founderReactions,
        wifeReactions,
        rerankedSourceMovieIds:
          sharedSession?.state === "reranked"
            ? sharedSession.rerankedSourceMovieIds
            : [],
      }),
    [founderReactions, sessionCandidates, sessionMode, sharedSession, wifeReactions],
  );

  const currentStepIndex = stepOrder.indexOf(step);
  const isSyncing = syncStatus !== "ready";

  function resetSession() {
    setStep("setup");
    setFounderIndex(0);
    setWifeIndex(0);
    setSessionCandidates(demoCandidates);
    setFounderReactions({});
    setWifeReactions({});
    setSharedSession(null);
    setDebugHistory(null);
    setDebugHistoryStatus("idle");
    setDebugHistoryMessage(null);
    setSyncStatus("ready");
    setSessionSource(apiHealth.connected ? "api" : "demo");
    setApiError(
      apiHealth.connected ? null : "API is disconnected, so this review is using demo data.",
    );
  }

  async function startSession() {
    setFounderIndex(0);
    setWifeIndex(0);
    setSessionCandidates(demoCandidates);
    setFounderReactions({});
    setWifeReactions({});
    setSharedSession(null);
    setDebugHistory(null);
    setDebugHistoryStatus("idle");
    setDebugHistoryMessage(null);

    if (!apiHealth.connected) {
      setSessionSource("demo");
      setApiError("API is disconnected, so this review is using demo data.");
      setStep("founder");
      return;
    }

    setSyncStatus("saving");
    setApiError(null);

    try {
      const shortlistResponse = await loadRecommendationShortlist({
        householdId: "default-household",
        activeMode: toApiSessionMode(sessionMode),
        participantIds,
        shortlistSize: setupLoad.setup.defaults.shortlistSize,
      });
      const candidates = shortlistResponse.shortlist.map(toSessionCandidate);
      setSessionCandidates(candidates);

      const session = await createSharedSession({
        householdId: "default-household",
        activeMode: toApiSessionMode(sessionMode),
        participantIds,
        shortlist: candidates.map((candidate, index) => ({
          sourceMovieId: candidate.id,
          title: candidate.title,
          candidateRank: index + 1,
        })),
      });

      setSharedSession(session);
      setSessionSource("api");
    } catch (error) {
      setSessionCandidates(demoCandidates);
      setSharedSession(null);
      setSessionSource("demo");
      setDebugHistoryStatus("failed");
      setDebugHistoryMessage("Debug evidence is unavailable because the session fell back to demo mode.");
      setApiError(toErrorMessage(error));
    } finally {
      setSyncStatus("ready");
      setStep("founder");
    }
  }

  async function recordReaction(
    actor: "founder" | "wife",
    candidateId: string,
    reaction: ReactionValue,
  ): Promise<void> {
    if (actor === "founder") {
      const nextReactions = { ...founderReactions, [candidateId]: reaction };
      setFounderReactions(nextReactions);

      if (founderIndex === sessionCandidates.length - 1) {
        await submitFirstPass(nextReactions);
        setStep("handoff");
        return;
      }

      setFounderIndex((current) => current + 1);
      return;
    }

    const nextReactions = { ...wifeReactions, [candidateId]: reaction };
    setWifeReactions(nextReactions);

    if (wifeIndex === sessionCandidates.length - 1) {
      await submitSecondPass(nextReactions);
      setStep("results");
      return;
    }

    setWifeIndex((current) => current + 1);
  }

  async function submitFirstPass(nextReactions: ReactionState): Promise<void> {
    if (sessionSource !== "api" || sharedSession === null) {
      return;
    }

    setSyncStatus("saving");
    setApiError(null);

    try {
      const session = await submitSessionReactions(sharedSession.sessionId, {
        participantId: participantIds[0],
        reactions: reactionsPayload(sessionCandidates, nextReactions),
      });
      setSharedSession(session);
    } catch (error) {
      setSessionSource("demo");
      setDebugHistoryStatus("failed");
      setDebugHistoryMessage("Debug evidence is unavailable because the session fell back to demo mode.");
      setApiError(toErrorMessage(error));
    } finally {
      setSyncStatus("ready");
    }
  }

  async function continueAfterHandoff(): Promise<void> {
    if (sessionSource !== "api" || sharedSession === null) {
      setStep("wife");
      return;
    }

    setSyncStatus("loading");
    setApiError(null);

    try {
      const session = await advanceSessionHandoff(sharedSession.sessionId);
      setSharedSession(session);
    } catch (error) {
      setSessionSource("demo");
      setDebugHistoryStatus("failed");
      setDebugHistoryMessage("Debug evidence is unavailable because the session fell back to demo mode.");
      setApiError(toErrorMessage(error));
    } finally {
      setSyncStatus("ready");
      setStep("wife");
    }
  }

  async function submitSecondPass(nextReactions: ReactionState): Promise<void> {
    if (sessionSource !== "api" || sharedSession === null) {
      return;
    }

    setSyncStatus("saving");
    setApiError(null);

    try {
      const session = await submitSessionReactions(sharedSession.sessionId, {
        participantId: participantIds[1],
        reactions: reactionsPayload(sessionCandidates, nextReactions),
      });
      setSharedSession(session);
    } catch (error) {
      setSessionSource("demo");
      setDebugHistoryStatus("failed");
      setDebugHistoryMessage("Debug evidence is unavailable because the session fell back to demo mode.");
      setApiError(toErrorMessage(error));
    } finally {
      setSyncStatus("ready");
    }
  }

  return (
    <main className="appShell">
      <header className="topBar">
        <div>
          <p className="eyebrow">Movie Night Mediator</p>
          <h1>Tonight</h1>
        </div>
        <div
          className={
            apiHealth.connected
              ? "connectionPill connectionPillConnected"
              : "connectionPill connectionPillDisconnected"
          }
          role="status"
          aria-label={`FastAPI health ${apiHealth.label}`}
          title={apiHealth.detail}
        >
          <span aria-hidden="true" />
          <strong>{apiHealth.label}</strong>
        </div>
      </header>

      <section className="statusStrip" aria-label="Current setup status">
        <div>
          <span>{setupLoad.source === "backend" ? "Setup ready" : "Demo setup"}</span>
          <p>{setupLoad.detail}</p>
        </div>
        <strong>{setupLoad.setup.defaults.shortlistSize} picks</strong>
      </section>

      <SessionSyncStrip
        source={sessionSource}
        status={syncStatus}
        apiError={apiError}
        sessionId={sharedSession?.sessionId}
      />

      <nav className="flowTabs" aria-label="Pass the phone steps">
        {stepOrder.map((item, index) => (
          <button
            key={item}
            type="button"
            className={item === step ? "flowTab flowTabActive" : "flowTab"}
            onClick={() => setStep(item)}
            aria-current={item === step ? "step" : undefined}
            disabled={isSyncing}
          >
            <span>{index + 1}</span>
            {stepLabels[item]}
          </button>
        ))}
      </nav>

      <div className="progressRail" aria-hidden="true">
        <span style={{ width: `${((currentStepIndex + 1) / stepOrder.length) * 100}%` }} />
      </div>

      {step === "setup" ? (
        <SetupStep
          founderLabel={founderLabel}
          wifeLabel={wifeLabel}
          setupLoad={setupLoad}
          sessionMode={sessionMode}
          onSessionModeChange={setSessionMode}
          isSyncing={isSyncing}
          onStart={startSession}
        />
      ) : null}

      {step === "founder" ? (
        <ReactionStep
          actorLabel={founderLabel}
          actor="founder"
          index={founderIndex}
          total={sessionCandidates.length}
          candidate={sessionCandidates[founderIndex]}
          selectedReaction={founderReactions[sessionCandidates[founderIndex].id]}
          isSyncing={isSyncing}
          onReaction={recordReaction}
          onBack={() => {
            if (founderIndex === 0) {
              setStep("setup");
              return;
            }

            setFounderIndex((current) => current - 1);
          }}
        />
      ) : null}

      {step === "handoff" ? (
        <HandoffStep
          founderLabel={founderLabel}
          wifeLabel={wifeLabel}
          founderReactions={founderReactions}
          isSyncing={isSyncing}
          onBack={() => setStep("founder")}
          onContinue={continueAfterHandoff}
        />
      ) : null}

      {step === "wife" ? (
        <ReactionStep
          actorLabel={wifeLabel}
          actor="wife"
          index={wifeIndex}
          total={sessionCandidates.length}
          candidate={sessionCandidates[wifeIndex]}
          selectedReaction={wifeReactions[sessionCandidates[wifeIndex].id]}
          isSyncing={isSyncing}
          onReaction={recordReaction}
          onBack={() => {
            if (wifeIndex === 0) {
              setStep("handoff");
              return;
            }

            setWifeIndex((current) => current - 1);
          }}
        />
      ) : null}

      {step === "results" ? (
        <ResultsStep
          founderLabel={founderLabel}
          wifeLabel={wifeLabel}
          rankedCandidates={rankedCandidates}
          founderReactions={founderReactions}
          wifeReactions={wifeReactions}
          sessionMode={sessionMode}
          sessionSource={sessionSource}
          sharedSession={sharedSession}
          debugHistory={debugHistory}
          debugHistoryStatus={debugHistoryStatus}
          debugHistoryMessage={debugHistoryMessage}
          onLoadDebugHistory={loadDebugHistory}
          onReset={resetSession}
        />
      ) : null}
    </main>
  );

  async function loadDebugHistory(): Promise<void> {
    if (sessionSource !== "api" || sharedSession === null) {
      setDebugHistory(null);
      setDebugHistoryStatus("failed");
      setDebugHistoryMessage("Debug evidence is only available for backend-backed sessions.");
      return;
    }

    setDebugHistoryStatus("loading");
    setDebugHistoryMessage(null);

    try {
      const history = await getSessionDebugHistory(sharedSession.sessionId);
      setDebugHistory(history);
      setDebugHistoryStatus("ready");
    } catch (error) {
      setDebugHistory(null);
      setDebugHistoryStatus("failed");
      setDebugHistoryMessage(toDebugHistoryErrorMessage(error));
    }
  }
}

function SetupStep({
  founderLabel,
  wifeLabel,
  setupLoad,
  sessionMode,
  onSessionModeChange,
  isSyncing,
  onStart,
}: {
  founderLabel: string;
  wifeLabel: string;
  setupLoad: SetupLoadResult;
  sessionMode: SessionMode;
  onSessionModeChange: (mode: SessionMode) => void;
  isSyncing: boolean;
  onStart: () => void;
}) {
  return (
    <section className="wizardPanel sessionPanel" aria-labelledby="setup-heading">
      <div className="sectionHeading">
        <p className="eyebrow">Pass the phone</p>
        <h2 id="setup-heading">Start a shared session</h2>
        <p>
          {founderLabel} reacts first, then hands the phone to {wifeLabel}.
        </p>
      </div>

      <div className="sessionSummaryGrid">
        <SummaryTile label="People" value={`${founderLabel} + ${wifeLabel}`} />
        <SummaryTile label="Watchability" value={setupLoad.setup.defaults.availabilityRegion} />
        <SummaryTile label="Language" value={setupLoad.setup.defaults.languageAccess} />
        <SummaryTile label="Shortlist" value="Five quick reactions each" />
      </div>

      <div className="modeBlock">
        <p className="controlLabel">Tonight's mode</p>
        <div className="segmentedControl" role="group" aria-label="Session mode">
          {(Object.keys(sessionModeLabels) as SessionMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={mode === sessionMode ? "segment segmentActive" : "segment"}
              onClick={() => onSessionModeChange(mode)}
            >
              {sessionModeLabels[mode]}
            </button>
          ))}
        </div>
      </div>

      <button
        type="button"
        className="primaryAction"
        onClick={onStart}
        disabled={isSyncing}
      >
        {isSyncing ? "Starting session..." : "Start first pass"}
      </button>
    </section>
  );
}

function ReactionStep({
  actorLabel,
  actor,
  index,
  total,
  candidate,
  selectedReaction,
  isSyncing,
  onReaction,
  onBack,
}: {
  actorLabel: string;
  actor: "founder" | "wife";
  index: number;
  total: number;
  candidate: DemoCandidate;
  selectedReaction: ReactionValue | undefined;
  isSyncing: boolean;
  onReaction: (
    actor: "founder" | "wife",
    candidateId: string,
    reaction: ReactionValue,
  ) => void | Promise<void>;
  onBack: () => void;
}) {
  return (
    <section className="wizardPanel reactionPanel" aria-labelledby="reaction-heading">
      <div className="reactionMeta">
        <p className="eyebrow">{actorLabel}'s pass</p>
        <strong>
          {index + 1} of {total}
        </strong>
      </div>

      <article className="movieCard">
        <img src={candidate.posterUrl} alt="" className="posterImage" />
        <div className="movieDetails">
          <span className="safePill">{candidate.safePickStatus}</span>
          <h2 id="reaction-heading">{candidate.title}</h2>
          <p className="movieFacts">
            {candidate.year} · {candidate.runtime}
          </p>
          <p>{candidate.reason}</p>
          <dl className="movieSignals">
            <div>
              <dt>Access</dt>
              <dd>{candidate.availability}</dd>
            </div>
            <div>
              <dt>Language</dt>
              <dd>{candidate.languageAccess}</dd>
            </div>
            <div>
              <dt>Tone</dt>
              <dd>{candidate.tone}</dd>
            </div>
          </dl>
        </div>
      </article>

      <div className="reactionGrid" role="group" aria-label={`Reaction for ${candidate.title}`}>
        {(Object.keys(reactionLabels) as ReactionValue[]).map((reaction) => (
          <button
            key={reaction}
            type="button"
            className={
              selectedReaction === reaction
                ? `reactionButton reactionButton${reaction} reactionButtonActive`
                : `reactionButton reactionButton${reaction}`
            }
            onClick={() => onReaction(actor, candidate.id, reaction)}
            disabled={isSyncing}
          >
            {reactionLabels[reaction]}
          </button>
        ))}
      </div>

      <button
        type="button"
        className="secondaryButton fullWidthButton"
        onClick={onBack}
        disabled={isSyncing}
      >
        Back
      </button>
    </section>
  );
}

function HandoffStep({
  founderLabel,
  wifeLabel,
  founderReactions,
  isSyncing,
  onBack,
  onContinue,
}: {
  founderLabel: string;
  wifeLabel: string;
  founderReactions: ReactionState;
  isSyncing: boolean;
  onBack: () => void;
  onContinue: () => void | Promise<void>;
}) {
  const counts = countReactions(founderReactions);

  return (
    <section className="wizardPanel handoffPanel" aria-labelledby="handoff-heading">
      <div className="handoffHero" aria-hidden="true">
        <span>{founderLabel.slice(0, 1)}</span>
        <strong>{wifeLabel.slice(0, 1)}</strong>
      </div>
      <div className="sectionHeading centerText">
        <p className="eyebrow">Handoff</p>
        <h2 id="handoff-heading">Pass the phone to {wifeLabel}</h2>
        <p>
          {founderLabel}'s reactions are saved for this session.{" "}
          {wifeLabel} gets the same five titles without seeing the first pass.
        </p>
      </div>

      <div className="handoffStats">
        <SummaryTile label="Interested" value={String(counts.interested)} />
        <SummaryTile label="Maybe" value={String(counts.maybe)} />
        <SummaryTile label="No" value={String(counts.no)} />
        <SummaryTile label="Seen" value={String(counts.seen)} />
      </div>

      <div className="bottomActions inlineActions">
        <button
          type="button"
          className="secondaryButton"
          onClick={onBack}
          disabled={isSyncing}
        >
          Back
        </button>
        <button type="button" onClick={onContinue} disabled={isSyncing}>
          {isSyncing ? "Saving handoff..." : "Start second pass"}
        </button>
      </div>
    </section>
  );
}

function SessionSyncStrip({
  source,
  status,
  apiError,
  sessionId,
}: {
  source: SessionSource;
  status: SyncStatus;
  apiError: string | null;
  sessionId: string | undefined;
}) {
  const label =
    status === "saving"
      ? "Saving"
      : status === "loading"
        ? "Loading"
        : source === "api"
          ? "API mode"
          : "Demo mode";
  const detail =
    status === "saving"
      ? "Saving this step to the session API."
      : status === "loading"
        ? "Loading the next session state from the API."
        : source === "api"
          ? sessionId
            ? `Backend session ${sessionId} is active.`
            : "The next session will try the backend API first."
          : "Local fixture scoring is active for this review.";

  return (
    <section
      className={apiError ? "syncStrip syncStripWarning" : "syncStrip"}
      aria-label="Session sync status"
      role="status"
    >
      <div>
        <span>{label}</span>
        <p>{apiError ?? detail}</p>
      </div>
    </section>
  );
}

function ResultsStep({
  founderLabel,
  wifeLabel,
  rankedCandidates,
  founderReactions,
  wifeReactions,
  sessionMode,
  sessionSource,
  sharedSession,
  debugHistory,
  debugHistoryStatus,
  debugHistoryMessage,
  onLoadDebugHistory,
  onReset,
}: {
  founderLabel: string;
  wifeLabel: string;
  rankedCandidates: RankedCandidate[];
  founderReactions: ReactionState;
  wifeReactions: ReactionState;
  sessionMode: SessionMode;
  sessionSource: SessionSource;
  sharedSession: SharedSessionPayload | null;
  debugHistory: DebugHistorySessionPayload | null;
  debugHistoryStatus: DebugHistoryStatus;
  debugHistoryMessage: string | null;
  onLoadDebugHistory: () => void | Promise<void>;
  onReset: () => void;
}) {
  const bestPick = rankedCandidates[0];

  return (
    <section className="wizardPanel resultsPanel" aria-labelledby="results-heading">
      <div className="sectionHeading">
        <p className="eyebrow">Best pick</p>
        <h2 id="results-heading">{bestPick.title}</h2>
        <p>
          {sessionModeLabels[sessionMode]} mode chose the title with the strongest shared
          signal after both reaction passes.
        </p>
      </div>

      <article className="winnerCard">
        <img src={bestPick.posterUrl} alt="" className="winnerPoster" />
        <div>
          <span className="safePill">{bestPick.safePickStatus}</span>
          <p className="winnerScore">{bestPick.score} shared score</p>
          <p>{bestPick.reason}</p>
          <div className="reactionPair">
            <ReactionBadge
              label={founderLabel}
              value={founderReactions[bestPick.id]}
            />
            <ReactionBadge label={wifeLabel} value={wifeReactions[bestPick.id]} />
          </div>
        </div>
      </article>

      <div className="rankedList" aria-label="Reranked shortlist">
        {rankedCandidates.map((candidate, index) => (
          <article key={candidate.id} className="rankedItem">
            <strong>{index + 1}</strong>
            <div>
              <h3>{candidate.title}</h3>
              <p>
                {candidate.score} points · {candidate.safePickStatus}
              </p>
              <div className="reactionPair">
                <ReactionBadge
                  label={founderLabel}
                  value={founderReactions[candidate.id]}
                />
                <ReactionBadge label={wifeLabel} value={wifeReactions[candidate.id]} />
              </div>
            </div>
          </article>
        ))}
      </div>

      <DebugHistoryPanel
        source={sessionSource}
        session={sharedSession}
        history={debugHistory}
        status={debugHistoryStatus}
        message={debugHistoryMessage}
        onLoad={onLoadDebugHistory}
      />

      <button type="button" className="primaryAction" onClick={onReset}>
        Start another session
      </button>
    </section>
  );
}

function DebugHistoryPanel({
  source,
  session,
  history,
  status,
  message,
  onLoad,
}: {
  source: SessionSource;
  session: SharedSessionPayload | null;
  history: DebugHistorySessionPayload | null;
  status: DebugHistoryStatus;
  message: string | null;
  onLoad: () => void | Promise<void>;
}) {
  const canLoad = source === "api" && session !== null;
  const bestPickTitle = history
    ? titleForSourceMovieId(history.shortlist, history.bestPickSourceMovieId)
    : null;

  return (
    <section className="debugHistoryPanel" aria-labelledby="debug-history-heading">
      <div className="debugHistoryHeader">
        <div>
          <p className="eyebrow">Debug history</p>
          <h3 id="debug-history-heading">Current session evidence</h3>
        </div>
        <button
          type="button"
          className="secondaryButton compactButton"
          onClick={onLoad}
          disabled={!canLoad || status === "loading"}
        >
          {status === "loading" ? "Loading..." : history ? "Refresh" : "Load"}
        </button>
      </div>

      {!canLoad ? (
        <p className="debugMessage">
          Demo sessions do not have persisted backend evidence.
        </p>
      ) : null}

      {message ? <p className="debugMessage">{message}</p> : null}

      {history ? (
        <div className="debugHistoryBody">
          <dl className="debugFacts">
            <div>
              <dt>State</dt>
              <dd>{history.state}</dd>
            </div>
            <div>
              <dt>Participants</dt>
              <dd>{history.participantIds.join(", ")}</dd>
            </div>
            <div>
              <dt>Best pick</dt>
              <dd>{bestPickTitle ?? history.bestPickSourceMovieId ?? "No pick yet"}</dd>
            </div>
          </dl>

          <DebugList
            label="Reranked order"
            items={history.rerankedSourceMovieIds.map((sourceMovieId) => {
              const title = titleForSourceMovieId(history.shortlist, sourceMovieId);

              return title ? `${title} (${sourceMovieId})` : sourceMovieId;
            })}
          />

          <DebugReactionList
            label="Founder reactions"
            reactions={history.founderReactions}
          />
          <DebugReactionList
            label="Wife reactions"
            reactions={history.wifeReactions}
          />
          <DebugRecommendationSnapshot history={history} />
          <DebugList
            label="Unavailable evidence"
            items={history.unavailableEvidence}
          />
        </div>
      ) : null}
    </section>
  );
}

function DebugRecommendationSnapshot({
  history,
}: {
  history: DebugHistorySessionPayload;
}) {
  const snapshot = history.recommendationSnapshot;

  if (snapshot === null) {
    return (
      <div className="debugListBlock">
        <h4>Scoring snapshot</h4>
        <p>No scoring snapshot saved yet.</p>
      </div>
    );
  }

  return (
    <div className="debugListBlock">
      <h4>Scoring snapshot</h4>
      <ol>
        {snapshot.candidates.map((candidate) => (
          <li key={candidate.sourceMovieId}>
            {formatDebugSnapshotCandidate(candidate)}
          </li>
        ))}
      </ol>
      {snapshot.isUncertain ? (
        <p>
          Uncertain: {snapshot.uncertaintyReason ?? "No reason saved."}
        </p>
      ) : null}
      {snapshot.recommendedFollowUp ? (
        <p>Follow-up: {snapshot.recommendedFollowUp}</p>
      ) : null}
    </div>
  );
}

function DebugReactionList({
  label,
  reactions,
}: {
  label: string;
  reactions: DebugHistoryReactionPayload[];
}) {
  return (
    <DebugList
      label={label}
      items={reactions.map(
        (reaction) =>
          `${reaction.participantId}: ${reaction.sourceMovieId} = ${reaction.reactionLabel}`,
      )}
    />
  );
}

function DebugList({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="debugListBlock">
      <h4>{label}</h4>
      {items.length > 0 ? (
        <ol>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ol>
      ) : (
        <p>No evidence saved yet.</p>
      )}
    </div>
  );
}

function formatDebugSnapshotCandidate(
  candidate: DebugHistoryRecommendationCandidatePayload,
): string {
  const userScores = candidate.userScores
    .map((score) => `${score.userId} ${score.score}`)
    .join(", ");
  const interestingPick = candidate.isInterestingPick ? ", interesting" : "";

  return `${candidate.candidateRank}. ${candidate.title}: ${candidate.groupScore} group, ${candidate.fitBucket}, ${userScores}${interestingPick}. ${candidate.whyShort}`;
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return (
    <article className="summaryTile">
      <span>{label}</span>
      <p>{value}</p>
    </article>
  );
}

function ReactionBadge({
  label,
  value,
}: {
  label: string;
  value: ReactionValue | undefined;
}) {
  return (
    <span className="reactionBadge">
      {label}: {value ? reactionLabels[value] : "No vote"}
    </span>
  );
}

type RankedCandidate = DemoCandidate & {
  score: number;
};

function rankCandidates({
  sessionMode,
  candidates,
  founderReactions,
  wifeReactions,
  rerankedSourceMovieIds,
}: {
  sessionMode: SessionMode;
  candidates: DemoCandidate[];
  founderReactions: ReactionState;
  wifeReactions: ReactionState;
  rerankedSourceMovieIds: string[];
}): RankedCandidate[] {
  const localRanked = candidates
    .map((candidate) => {
      const founderReaction = founderReactions[candidate.id];
      const wifeReaction = wifeReactions[candidate.id];
      const founderScore = candidate.taste.founder + reactionScore(founderReaction);
      const wifeScore = candidate.taste.wife + reactionScore(wifeReaction);
      const seenPenalty =
        founderReaction === "seen" || wifeReaction === "seen" ? 100 : 0;
      const noPenalty =
        founderReaction === "no" || wifeReaction === "no"
          ? sessionMode === "compromise"
            ? 38
            : 24
          : 0;
      const statusPenalty = candidate.safePickStatus === "Needs Quick Check" ? 14 : 0;
      const modeScore =
        sessionMode === "founder-first"
          ? founderScore * 0.58 + wifeScore * 0.42
          : sessionMode === "wife-first"
            ? founderScore * 0.42 + wifeScore * 0.58
            : Math.min(founderScore, wifeScore) * 0.65 +
              ((founderScore + wifeScore) / 2) * 0.35;

      return {
        ...candidate,
        score: Math.max(
          0,
          Math.round(modeScore - statusPenalty - noPenalty - seenPenalty),
        ),
      };
    })
    .sort((first, second) => {
      if (second.score !== first.score) {
        return second.score - first.score;
      }

      return first.baseRank - second.baseRank;
    });

  if (rerankedSourceMovieIds.length === 0) {
    return localRanked;
  }

  const apiRankById = new Map(
    rerankedSourceMovieIds.map((sourceMovieId, index) => [sourceMovieId, index]),
  );

  return localRanked
    .slice()
    .sort(
      (first, second) =>
        (apiRankById.get(first.id) ?? Number.MAX_SAFE_INTEGER) -
        (apiRankById.get(second.id) ?? Number.MAX_SAFE_INTEGER),
    );
}

function reactionScore(reaction: ReactionValue | undefined) {
  if (reaction === "interested") {
    return 18;
  }

  if (reaction === "maybe") {
    return 6;
  }

  if (reaction === "no") {
    return -34;
  }

  if (reaction === "seen") {
    return -45;
  }

  return 0;
}

function countReactions(reactions: ReactionState): Record<ReactionValue, number> {
  return {
    interested: Object.values(reactions).filter((reaction) => reaction === "interested")
      .length,
    maybe: Object.values(reactions).filter((reaction) => reaction === "maybe").length,
    no: Object.values(reactions).filter((reaction) => reaction === "no").length,
    seen: Object.values(reactions).filter((reaction) => reaction === "seen").length,
  };
}

function reactionsPayload(
  candidates: DemoCandidate[],
  reactions: ReactionState,
) {
  return candidates.map((candidate) => ({
    sourceMovieId: candidate.id,
    reactionLabel: reactions[candidate.id] ?? "maybe",
  }));
}

function toSessionCandidate(
  candidate: ShortlistCandidatePayload,
  index: number,
): DemoCandidate {
  const fixture = demoCandidates.find(
    (demoCandidate) =>
      demoCandidate.id === candidate.sourceMovieId ||
      demoCandidate.title.toLowerCase() === candidate.title.toLowerCase(),
  );
  const rank = candidate.candidateRank || index + 1;
  const groupScore = candidate.groupScore ?? 72;

  return {
    id: candidate.sourceMovieId,
    title: candidate.title,
    year: candidate.year ?? fixture?.year ?? new Date().getFullYear(),
    runtime: candidate.runtime ?? fixture?.runtime ?? "Runtime check needed",
    posterUrl: candidate.posterUrl ?? fixture?.posterUrl ?? fallbackPosterUrl,
    safePickStatus: toSafePickStatus(candidate.safePickStatus),
    availability:
      candidate.availability ??
      fixture?.availability ??
      "Availability check needed",
    languageAccess:
      candidate.languageAccess ??
      fixture?.languageAccess ??
      "Language access check needed",
    tone: candidate.tone ?? candidate.fitBucket ?? fixture?.tone ?? "Balanced pick",
    reason:
      candidate.reason ??
      fixture?.reason ??
      "Recommended by the backend shortlist for tonight's shared session.",
    baseRank: rank,
    taste: {
      founder: candidate.founderScore ?? fixture?.taste.founder ?? groupScore,
      wife: candidate.wifeScore ?? fixture?.taste.wife ?? groupScore,
    },
  };
}

function toSafePickStatus(
  value: string | null | undefined,
): DemoCandidate["safePickStatus"] {
  return value === "Needs Quick Check" ? "Needs Quick Check" : "Safe Pick";
}

function titleForSourceMovieId(
  shortlist: { sourceMovieId: string; title: string }[],
  sourceMovieId: string | null,
): string | null {
  if (sourceMovieId === null) {
    return null;
  }

  return (
    shortlist.find((candidate) => candidate.sourceMovieId === sourceMovieId)?.title ??
    null
  );
}

function toErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return `${error.message} Continuing in demo mode.`;
  }

  return "Session API failed. Continuing in demo mode.";
}

function toDebugHistoryErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return `${error.message} Debug evidence is unavailable.`;
  }

  return "Debug history could not be loaded.";
}
