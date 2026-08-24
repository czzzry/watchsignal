"use client";

import { useEffect, useState } from "react";
import { describeSharedWhy, fallbackPosterUrl } from "../../pass-the-phone-helpers";
import type {
  DebugHistoryStatus,
  PeopleMode,
  RankedCandidate,
  ReactionState,
  SessionSource,
} from "../../pass-the-phone-model";
import type {
  DebugHistorySessionPayload,
  RecommendationRunStatus,
  SharedSessionPayload,
  TasteProfileSummaryPayload,
  TonightIntentInterpretationPayload,
} from "../../session-client";
import { ContinuationSteerPanel } from "../continuation-steer-panel";
import {
  createReviewDiagnosticRequests,
  reviewSurfaceContract,
} from "../review-mode-contract";
import { SessionRecoveryStep } from "../session-recovery-step";
import { OutcomeUtility } from "./outcome-utility";
import { RankedResultStage } from "./ranked-result-stage";
import {
  DebugHistoryPanel,
  RecommendationEvidencePanel,
  type ResultsParticipantEntry,
  SessionEvidencePanel,
} from "./results-panels";
import {
  ResultUtilityHub,
  type ResultUtilityView,
} from "./result-utility-hub";
import { useResultsPersistence } from "./use-results-persistence";
import { WatchlistUtility } from "./watchlist-utility";

export type ResultsScreenModel = {
  household: {
    founderLabel: string;
    wifeLabel: string;
    participantIds: string[];
    peopleMode: PeopleMode;
  };
  result: {
    rankedCandidates: RankedCandidate[];
    founderReactions: ReactionState;
    wifeReactions: ReactionState;
    sessionSource: SessionSource;
    sharedSession: SharedSessionPayload | null;
    recommendationSource: string;
    recommendationRunStatus: RecommendationRunStatus | null;
    availabilityRegion: string;
  };
  continuation: {
    activeTonightIntents: TonightIntentInterpretationPayload[];
    movieSource: "live" | "local";
    steerText: string;
    pendingSteerIntent: TonightIntentInterpretationPayload | null;
    steerClarificationText: string;
    steerMessage: string | null;
    error: string | null;
    canShowMore: boolean;
    isSyncing: boolean;
  };
  diagnostics: {
    reviewMode: boolean;
    debugHistory: DebugHistorySessionPayload | null;
    tasteProfileSummaries: TasteProfileSummaryPayload[];
    debugHistoryStatus: DebugHistoryStatus;
    debugHistoryMessage: string | null;
  };
};

export type ResultsScreenActions = {
  household: {
    refreshProfileMemory: () => void | Promise<void>;
  };
  result: {
    startNewNight: () => void;
  };
  continuation: {
    changeText: (text: string) => void;
    interpret: () => void | Promise<void>;
    changeClarificationText: (text: string) => void;
    answerClarification: () => void | Promise<void>;
    add: () => void;
    apply: () => void | Promise<void>;
    showMore: () => void | Promise<void>;
  };
  diagnostics: {
    loadDebugHistory: () => void | Promise<void>;
  };
};

export function ResultsScreen({
  model,
  actions,
}: {
  model: ResultsScreenModel;
  actions: ResultsScreenActions;
}) {
  const { household, result, continuation, diagnostics } = model;
  const bestPick = result.rankedCandidates[0];
  const [continuationOpen, setContinuationOpen] = useState(false);
  const [utilityView, setUtilityView] = useState<ResultUtilityView>("home");
  const reviewSurface = reviewSurfaceContract(diagnostics.reviewMode);
  const diagnosticRequests = createReviewDiagnosticRequests(diagnostics.reviewMode, {
    loadDebugHistory: actions.diagnostics.loadDebugHistory,
    loadSessionTasteEvidence: async () => {},
    loadSoloTasteEvidence: async () => {},
  });
  const participantEntries = resultsParticipantEntries(household);
  const persistence = useResultsPersistence({
    sessionSource: result.sessionSource,
    sharedSession: result.sharedSession,
    participantIds: household.participantIds,
    participantEntries,
    rankedCandidates: result.rankedCandidates,
    bestPick,
    diagnosticRequests,
    onRefreshProfileMemory: actions.household.refreshProfileMemory,
  });
  const {
    canPersist,
    canSaveWatchlist,
    outcomeType,
    otherPickId,
    outcomeNote,
    savedOutcome,
    outcomeError,
    feedbackState,
    feedbackNotes,
    savedFeedback,
    feedbackError,
    feedbackReady,
    watchedTitle,
    watchlistEntries,
    watchlistStatus,
    watchlistMessage,
    watchlistEntryBusy,
    watchlistWatchedState,
    watchlistRatingState,
    bestPickWatchlistEntry,
    outcomeBusy,
    outcomeConfirmed,
    feedbackBusy,
    refreshWatchlist,
    handleOutcomeTypeChange,
    handleOtherPickChange,
    handleOutcomeNoteChange,
    handleFeedbackChange,
    handleFeedbackNoteChange,
    handleWatchlistRatingChange,
    handleSaveBestPick,
    handleRemoveWatchlistEntry,
    handleMarkWatchlistEntryWatched,
    handleSaveOutcome,
    handleSaveFeedback,
  } = persistence;

  useEffect(() => {
    if (
      !canPersist ||
      result.sharedSession === null ||
      diagnostics.debugHistory !== null ||
      diagnostics.debugHistoryStatus !== "idle"
    ) {
      return;
    }

    void diagnosticRequests.initialResults();
  }, [
    canPersist,
    result.sharedSession?.sessionId,
    result.sharedSession?.state,
    diagnostics.debugHistory,
    diagnostics.debugHistoryStatus,
    diagnosticRequests,
  ]);

  if (!bestPick) {
    return (
      <SessionRecoveryStep
        title="No ranked pick yet"
        detail="This session finished without a shortlist to rank. Start another session to load a fresh set of picks."
        actionLabel="Start another session"
        onAction={actions.result.startNewNight}
      />
    );
  }

  const sharedReasons = Object.fromEntries(
    result.rankedCandidates.slice(0, 5).map((candidate) => [
      candidate.id,
      compactResultReason(
        describeSharedWhy({
          candidate,
          founderReaction: result.founderReactions[candidate.id],
          wifeReaction: result.wifeReactions[candidate.id],
          peopleMode: household.peopleMode,
          founderLabel: household.founderLabel,
          wifeLabel: household.wifeLabel,
        }),
      ),
    ]),
  );
  const continuationContent = (
    <ContinuationSteerPanel
      activeIntents={continuation.activeTonightIntents}
      text={continuation.steerText}
      pendingIntent={continuation.pendingSteerIntent}
      clarificationText={continuation.steerClarificationText}
      message={continuation.steerMessage}
      continuationError={continuation.error}
      busy={continuation.isSyncing}
      canContinue={continuation.canShowMore}
      canSteer={continuation.movieSource === "live"}
      onTextChange={actions.continuation.changeText}
      onInterpret={actions.continuation.interpret}
      onClarificationTextChange={actions.continuation.changeClarificationText}
      onAnswerClarification={actions.continuation.answerClarification}
      onAdd={actions.continuation.add}
      onApply={actions.continuation.apply}
      onContinue={actions.continuation.showMore}
    />
  );
  const utilityContent = (
    <div className="resultUtilityStack">
      {result.recommendationRunStatus ? (
        <section className="recommendationRunStatus" role="status">
          <strong>{result.recommendationRunStatus.label}</strong>
          <p>{result.recommendationRunStatus.detail}</p>
          {result.recommendationRunStatus.curatorLens ? (
            <p>
              Taste Lens {result.recommendationRunStatus.curatorLens.status === "active" ? "ACTIVE" : "NOT APPLIED"}
              {" · "}{result.recommendationRunStatus.curatorLens.source}
            </p>
          ) : null}
        </section>
      ) : null}
      <ResultUtilityHub
        view={utilityView}
        winnerTitle={bestPick.title}
        saved={Boolean(bestPickWatchlistEntry)}
        saveBusy={watchlistStatus === "saving" || Boolean(watchlistEntryBusy[bestPick.id])}
        saveMessage={watchlistMessage}
        canSave={canSaveWatchlist}
        watchlistCount={watchlistEntries.length}
        onView={setUtilityView}
        onToggleSave={() => bestPickWatchlistEntry
          ? handleRemoveWatchlistEntry(bestPick.id)
          : handleSaveBestPick()}
        onReset={actions.result.startNewNight}
      >
        {utilityView === "watchlist" ? (
          <WatchlistUtility
            entries={watchlistEntries}
            participants={participantEntries}
            available={canSaveWatchlist}
            loading={watchlistStatus === "loading"}
            message={watchlistMessage}
            ratingState={watchlistRatingState}
            entryBusy={watchlistEntryBusy}
            watchedState={watchlistWatchedState}
            onBack={() => setUtilityView("home")}
            onRetry={refreshWatchlist}
            onRating={handleWatchlistRatingChange}
            onWatched={handleMarkWatchlistEntryWatched}
            onRemove={handleRemoveWatchlistEntry}
          />
        ) : utilityView === "outcome" ? (
          <OutcomeUtility
            rankedCandidates={result.rankedCandidates}
            participants={participantEntries}
            outcomeType={outcomeType}
            otherPickId={otherPickId}
            note={outcomeNote}
            savedOutcome={savedOutcome}
            watchedTitle={watchedTitle}
            outcomeError={outcomeError}
            feedbackError={feedbackError}
            feedbackState={feedbackState}
            feedbackNotes={feedbackNotes}
            outcomeBusy={outcomeBusy}
            outcomeConfirmed={outcomeConfirmed}
            feedbackBusy={feedbackBusy}
            canPersist={canPersist}
            canSaveOutcome={persistence.canSaveOutcome}
            feedbackReady={feedbackReady}
            savedFeedbackProfileIds={savedFeedback.map((item) => item.userId)}
            onBack={() => setUtilityView("home")}
            onOutcomeType={handleOutcomeTypeChange}
            onOtherPick={handleOtherPickChange}
            onNote={handleOutcomeNoteChange}
            onSaveOutcome={handleSaveOutcome}
            onFeedback={handleFeedbackChange}
            onFeedbackNote={handleFeedbackNoteChange}
            onSaveFeedback={handleSaveFeedback}
            onPosterFallback={handlePosterFallback}
          />
        ) : null}
      </ResultUtilityHub>
      {reviewSurface.showEvidence ? (
        <SessionEvidencePanel>
          <RecommendationEvidencePanel
            bestPick={bestPick}
            activeIntents={continuation.activeTonightIntents}
            recommendationSource={result.recommendationSource}
            availabilityRegion={result.availabilityRegion}
            peopleMode={household.peopleMode}
            participantEntries={participantEntries}
            tasteProfileSummaries={diagnostics.tasteProfileSummaries}
            debugHistory={diagnostics.debugHistory}
          />
          <DebugHistoryPanel
            source={result.sessionSource}
            session={result.sharedSession}
            history={diagnostics.debugHistory}
            tasteProfileSummaries={diagnostics.tasteProfileSummaries}
            status={diagnostics.debugHistoryStatus}
            message={diagnostics.debugHistoryMessage}
            onLoad={actions.diagnostics.loadDebugHistory}
          />
        </SessionEvidencePanel>
      ) : null}
    </div>
  );

  return (
    <RankedResultStage
      rankedCandidates={result.rankedCandidates}
      peopleMode={household.peopleMode}
      founderReactions={result.founderReactions}
      wifeReactions={result.wifeReactions}
      sharedReasons={sharedReasons}
      continuationOpen={continuationOpen}
      continuationContent={continuationContent}
      continuationAvailable
      utilityContent={utilityContent}
      onReset={actions.result.startNewNight}
      onToggleContinuation={() => setContinuationOpen((current) => !current)}
      onPosterFallback={handlePosterFallback}
    />
  );
}

function resultsParticipantEntries(
  household: ResultsScreenModel["household"],
): ResultsParticipantEntry[] {
  if (household.peopleMode === "couple") {
    return [
      { id: household.participantIds[0], label: household.founderLabel, actor: "founder" },
      { id: household.participantIds[1], label: household.wifeLabel, actor: "wife" },
    ];
  }

  return household.peopleMode === "founder"
    ? [{ id: household.participantIds[0], label: household.founderLabel, actor: "founder" }]
    : [{ id: household.participantIds[0], label: household.wifeLabel, actor: "wife" }];
}

function handlePosterFallback(event: { currentTarget: HTMLImageElement }): void {
  if (event.currentTarget.src !== fallbackPosterUrl) {
    event.currentTarget.src = fallbackPosterUrl;
  }
}

function compactResultReason(value: string): string {
  const normalized = value.trim().replace(/\s+/g, " ");
  if (normalized.length <= 96) {
    return normalized.replace(/[.!?]?$/, ".");
  }
  return `${normalized.slice(0, 93).trimEnd()}…`;
}
