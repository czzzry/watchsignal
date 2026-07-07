"use client";

import type { ReactNode } from "react";
import { reactionLabels } from "../../session-fixtures";
import {
  formatDebugCandidateInput,
  formatDebugSnapshotCandidate,
  titleForSourceMovieId,
  toMatchTier,
} from "../../pass-the-phone-helpers";
import type {
  DebugHistoryStatus,
  FeedbackNoteState,
  FeedbackState,
  PeopleMode,
  RankedCandidate,
  ReactionState,
  SessionSource,
} from "../../pass-the-phone-model";
import type {
  DebugHistoryCandidateInputPayload,
  DebugHistoryReactionPayload,
  DebugHistorySessionPayload,
  SessionOutcomePayload,
  SessionOutcomeType,
  SharedSessionPayload,
  TasteProfileSummaryPayload,
  TonightIntentInterpretationPayload,
  WatchlistEntryPayload,
} from "../../session-client";

export const feedbackLabels: Record<"loved" | "fine" | "no", string> = {
  loved: "Loved",
  fine: "Fine",
  no: "No",
};

export type ResultsParticipantEntry = {
  id: string;
  label: string;
  actor: "founder" | "wife";
};

type PosterFallbackHandler = (event: { currentTarget: HTMLImageElement }) => void;
type WatchlistStatus = "idle" | "loading" | "saving" | "removing" | "marking";

export function WinnerReveal({
  bestPick,
  peopleMode,
  participantEntries,
  founderReactions,
  wifeReactions,
  founderLabel,
  wifeLabel,
  sharedWhy,
  onPosterFallback,
}: {
  bestPick: RankedCandidate;
  peopleMode: PeopleMode;
  participantEntries: ResultsParticipantEntry[];
  founderReactions: ReactionState;
  wifeReactions: ReactionState;
  founderLabel: string;
  wifeLabel: string;
  sharedWhy: string;
  onPosterFallback: PosterFallbackHandler;
}) {
  const matchTier = toMatchTier(bestPick.score);

  return (
    <section className="winnerReveal">
      <article className="winnerPosterCard">
        <img
          src={bestPick.posterUrl}
          alt=""
          className="winnerPosterTall"
          onError={onPosterFallback}
        />
      </article>

      <div className={`matchPulse matchPulse${matchTier} resultsPulse`} aria-label={`Shared score ${bestPick.score}%`}>
        <span className="scoreSparkle" aria-hidden="true">✦</span>
        <span className="matchPulseLabel">Shared score</span>
        <strong>{bestPick.score}%</strong>
        <span className="scoreSparkle" aria-hidden="true">✦</span>
      </div>

      <div className="winnerRevealMeta">
        <h3>{bestPick.title}</h3>
        <p>
          {bestPick.year} · {bestPick.runtime} · {bestPick.genres.slice(0, 2).join(", ")}
        </p>
      </div>

      <div className="sharedWhyCard resultsSharedWhy">
        <span>Why this won</span>
        <p>{sharedWhy}</p>
      </div>

      <p className="resultsPeopleLabel">How you both felt</p>
      <div className={peopleMode === "couple" ? "resultsPeoplePanel resultsPeoplePanelCouple" : "resultsPeoplePanel"}>
        {(peopleMode === "couple" ? participantEntries.slice(0, 1) : participantEntries).map((participant) => (
          <ResultsPerson
            key={participant.id}
            participant={participant}
            bestPickId={bestPick.id}
            founderReactions={founderReactions}
            wifeReactions={wifeReactions}
            founderLabel={founderLabel}
            wifeLabel={wifeLabel}
          />
        ))}
        {peopleMode === "couple" ? (
          <div className="resultsHeartLockup" aria-hidden="true">
            <HeartPulseIcon />
          </div>
        ) : null}
        {(peopleMode === "couple" ? participantEntries.slice(1) : []).map((participant) => (
          <ResultsPerson
            key={participant.id}
            participant={participant}
            bestPickId={bestPick.id}
            founderReactions={founderReactions}
            wifeReactions={wifeReactions}
            founderLabel={founderLabel}
            wifeLabel={wifeLabel}
            avatarFirst
          />
        ))}
      </div>
    </section>
  );
}

function ResultsPerson({
  participant,
  bestPickId,
  founderReactions,
  wifeReactions,
  founderLabel,
  wifeLabel,
  avatarFirst = false,
}: {
  participant: ResultsParticipantEntry;
  bestPickId: string;
  founderReactions: ReactionState;
  wifeReactions: ReactionState;
  founderLabel: string;
  wifeLabel: string;
  avatarFirst?: boolean;
}) {
  const reaction =
    participant.actor === "founder"
      ? founderReactions[bestPickId]
      : wifeReactions[bestPickId];
  const label = reaction ? reactionLabels[reaction] : "No vote";
  const avatar = <div className="resultsPersonAvatar">{participant.label.slice(0, 1)}</div>;
  const meta = (
    <div className="resultsPersonMeta">
      <strong>{participant.actor === "founder" ? founderLabel : wifeLabel}</strong>
      <span>{label}</span>
    </div>
  );

  return (
    <div className="resultsPerson">
      {avatarFirst ? avatar : meta}
      {avatarFirst ? meta : avatar}
    </div>
  );
}

export function BackupTitles({
  rankedCandidates,
  onPosterFallback,
}: {
  rankedCandidates: RankedCandidate[];
  onPosterFallback: PosterFallbackHandler;
}) {
  return (
    <section className="resultsBackupsSection" aria-labelledby="backups-heading">
      <p id="backups-heading" className="resultsBackupsLabel">Backups we also liked</p>
      <div className="backupStrip" aria-label="Reranked shortlist">
        {rankedCandidates.slice(1).map((candidate) => (
          <article key={candidate.id} className="backupCard backupCardCompact">
            <img
              src={candidate.posterUrl}
              alt=""
              className="backupPoster backupPosterCompact"
              loading="eager"
              decoding="sync"
              onError={onPosterFallback}
            />
            <div className="backupMeta backupMetaCompact">
              <strong>{candidate.title}</strong>
              <span>{candidate.score}%</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function ResultsActions({
  canPersist,
  isSyncing,
  isBestPickSaved,
  watchlistStatus,
  onShowMore,
  onSaveBestPick,
  onReset,
}: {
  canPersist: boolean;
  isSyncing: boolean;
  isBestPickSaved: boolean;
  watchlistStatus: WatchlistStatus;
  onShowMore: () => void | Promise<void>;
  onSaveBestPick: () => void | Promise<void>;
  onReset: () => void;
}) {
  return (
    <>
      <div className="resultsActionRow" role="group" aria-label="Results actions">
        <button
          type="button"
          className="resultsPrimaryAction"
          onClick={onShowMore}
          disabled={!canPersist || isSyncing}
        >
          <span>{isSyncing ? "Finding five more..." : "Show 5 more"}</span>
          <RedoIcon />
        </button>
        <button
          type="button"
          className="secondaryButton resultsSecondaryAction"
          onClick={onSaveBestPick}
          disabled={!canPersist || watchlistStatus === "saving"}
        >
          <span>
            {watchlistStatus === "saving"
              ? "Saving..."
              : isBestPickSaved
                ? "Saved for later"
                : "Add to watchlist"}
          </span>
          <BookmarkIcon />
        </button>
      </div>

      <button type="button" className="secondaryButton resultsNewNightAction" onClick={onReset}>
        <RedoIcon />
        <span>Start new night</span>
      </button>
    </>
  );
}

export function WatchlistPanel({
  entries,
  participantEntries,
  status,
  ratingState,
  onRatingChange,
  onMarkWatched,
  onRemove,
  onPosterFallback,
}: {
  entries: WatchlistEntryPayload[];
  participantEntries: ResultsParticipantEntry[];
  status: WatchlistStatus;
  ratingState: Record<string, Record<string, "loved" | "fine" | "no">>;
  onRatingChange: (
    sourceMovieId: string,
    profileId: string,
    rating: "loved" | "fine" | "no",
  ) => void;
  onMarkWatched: (entry: WatchlistEntryPayload) => void | Promise<void>;
  onRemove: (sourceMovieId: string) => void | Promise<void>;
  onPosterFallback: PosterFallbackHandler;
}) {
  return (
    <section className="watchlistPanel" aria-labelledby="watchlist-heading">
      <div className="watchlistPanelHeader">
        <div>
          <p className="eyebrow">Shared household watchlist</p>
          <h3 id="watchlist-heading">Saved for later</h3>
        </div>
        <span>{entries.length}</span>
      </div>
      {entries.length > 0 ? (
        <div className="watchlistList">
          {entries.map((entry) => (
            <WatchlistItem
              key={entry.sourceMovieId}
              entry={entry}
              participantEntries={participantEntries}
              status={status}
              ratingState={ratingState}
              onRatingChange={onRatingChange}
              onMarkWatched={onMarkWatched}
              onRemove={onRemove}
              onPosterFallback={onPosterFallback}
            />
          ))}
        </div>
      ) : (
        <p className="watchlistEmpty">
          {status === "loading"
            ? "Loading saved movies..."
            : "Saved movies will appear here for the whole household."}
        </p>
      )}
    </section>
  );
}

function WatchlistItem({
  entry,
  participantEntries,
  status,
  ratingState,
  onRatingChange,
  onMarkWatched,
  onRemove,
  onPosterFallback,
}: {
  entry: WatchlistEntryPayload;
  participantEntries: ResultsParticipantEntry[];
  status: WatchlistStatus;
  ratingState: Record<string, Record<string, "loved" | "fine" | "no">>;
  onRatingChange: (
    sourceMovieId: string,
    profileId: string,
    rating: "loved" | "fine" | "no",
  ) => void;
  onMarkWatched: (entry: WatchlistEntryPayload) => void | Promise<void>;
  onRemove: (sourceMovieId: string) => void | Promise<void>;
  onPosterFallback: PosterFallbackHandler;
}) {
  const savedByLabel = entry.savedByProfileId
    ? entry.savedByDisplayLabel ??
      participantEntries.find((participant) => participant.id === entry.savedByProfileId)?.label ??
      entry.savedByProfileId
    : null;

  return (
    <article className="watchlistItem">
      {entry.posterUrl ? (
        <img
          src={entry.posterUrl}
          alt=""
          onError={onPosterFallback}
        />
      ) : null}
      <div>
        <strong>{entry.title}</strong>
        <p>
          {entry.releaseYear ? `${entry.releaseYear}` : "Saved movie"}
          {savedByLabel ? ` · Saved by ${savedByLabel}` : ""}
        </p>
      </div>
      <div className="watchlistActions">
        <button
          type="button"
          className="secondaryButton compactButton"
          onClick={() => onMarkWatched(entry)}
          disabled={status === "marking"}
        >
          {status === "marking" ? "Saving..." : "Watched"}
        </button>
        <button
          type="button"
          className="secondaryButton compactButton"
          onClick={() => onRemove(entry.sourceMovieId)}
          disabled={status === "removing"}
        >
          Remove
        </button>
      </div>
      <div className="watchlistRatingGrid">
        {participantEntries.map((participant) => (
          <div key={participant.id} className="watchlistRatingRow">
            <span>{participant.label}</span>
            <div role="group" aria-label={`${participant.label} rating for ${entry.title}`}>
              {(Object.keys(feedbackLabels) as Array<keyof typeof feedbackLabels>).map((label) => (
                <button
                  key={label}
                  type="button"
                  className={
                    ratingState[entry.sourceMovieId]?.[participant.id] === label
                      ? "watchlistRatingChip watchlistRatingChipActive"
                      : "watchlistRatingChip"
                  }
                  onClick={() => onRatingChange(entry.sourceMovieId, participant.id, label)}
                >
                  {feedbackLabels[label]}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

export function OutcomePanel({
  rankedCandidates,
  bestPick,
  participantEntries,
  participantCount,
  outcomeType,
  otherPickId,
  outcomeNote,
  savedOutcome,
  watchedTitle,
  canSaveOutcome,
  outcomeError,
  feedbackError,
  feedbackState,
  feedbackNotes,
  savedFeedbackCount,
  feedbackReady,
  onOutcomeTypeChange,
  onOtherPickChange,
  onOutcomeNoteChange,
  onSaveOutcome,
  onFeedbackChange,
  onFeedbackNoteChange,
  onSaveFeedback,
}: {
  rankedCandidates: RankedCandidate[];
  bestPick: RankedCandidate;
  participantEntries: ResultsParticipantEntry[];
  participantCount: number;
  outcomeType: SessionOutcomeType | null;
  otherPickId: string | null;
  outcomeNote: string;
  savedOutcome: SessionOutcomePayload | null;
  watchedTitle: RankedCandidate | null;
  canSaveOutcome: boolean;
  outcomeError: string | null;
  feedbackError: string | null;
  feedbackState: FeedbackState;
  feedbackNotes: FeedbackNoteState;
  savedFeedbackCount: number;
  feedbackReady: boolean;
  onOutcomeTypeChange: (outcomeType: SessionOutcomeType) => void;
  onOtherPickChange: (sourceMovieId: string) => void;
  onOutcomeNoteChange: (note: string) => void;
  onSaveOutcome: () => void | Promise<void>;
  onFeedbackChange: (participantId: string, feedback: keyof typeof feedbackLabels) => void;
  onFeedbackNoteChange: (participantId: string, note: string) => void;
  onSaveFeedback: () => void | Promise<void>;
}) {
  return (
    <details className="disclosurePanel outcomeDisclosure">
      <summary>Save what happened after</summary>
      <div className="disclosureBody">
        <section className="outcomePanel" aria-labelledby="outcome-heading">
          <div className="sectionHeading">
            <p className="eyebrow">After the movie</p>
            <h3 id="outcome-heading">What actually happened?</h3>
            <p>Save tonight&apos;s real outcome so the app can learn from more than shortlist taps.</p>
          </div>

          <div className="outcomeOptionGrid" role="group" aria-label="Outcome type">
            <button
              type="button"
              className={outcomeType === "watched_recommended" ? "segment segmentActive" : "segment"}
              onClick={() => onOutcomeTypeChange("watched_recommended")}
            >
              Watched best pick
            </button>
            <button
              type="button"
              className={outcomeType === "watched_other" ? "segment segmentActive" : "segment"}
              onClick={() => onOutcomeTypeChange("watched_other")}
            >
              Watched another shortlist title
            </button>
            <button
              type="button"
              className={outcomeType === "watched_nothing" ? "segment segmentActive" : "segment"}
              onClick={() => onOutcomeTypeChange("watched_nothing")}
            >
              Watched nothing
            </button>
          </div>

          {outcomeType === "watched_other" ? (
            <div className="outcomeChoiceList" role="group" aria-label="Other watched shortlist title">
              {rankedCandidates
                .filter((candidate) => candidate.id !== bestPick.id)
                .map((candidate) => (
                  <button
                    key={candidate.id}
                    type="button"
                    className={otherPickId === candidate.id ? "secondaryButton choiceButton choiceButtonActive" : "secondaryButton choiceButton"}
                    onClick={() => onOtherPickChange(candidate.id)}
                  >
                    {candidate.title}
                  </button>
                ))}
            </div>
          ) : null}

          <label className="noteField">
            <span>Optional note</span>
            <textarea
              value={outcomeNote}
              onChange={(event) => onOutcomeNoteChange(event.target.value)}
              rows={3}
              placeholder="Anything worth remembering about tonight?"
            />
          </label>

          <div className="bottomActions inlineActions">
            <button
              type="button"
              className="primaryAction"
              onClick={onSaveOutcome}
              disabled={!canSaveOutcome}
            >
              {savedOutcome ? "Outcome saved" : "Save outcome"}
            </button>
          </div>
          {outcomeError ? <p className="debugMessage quietCallout">{outcomeError}</p> : null}
        </section>

        {savedOutcome && savedOutcome.outcomeType !== "watched_nothing" && watchedTitle ? (
          <section className="outcomePanel" aria-labelledby="feedback-heading">
            <div className="sectionHeading">
              <p className="eyebrow">Post-watch feedback</p>
              <h3 id="feedback-heading">How did each of you feel?</h3>
              <p>These are separate from the shortlist reactions and count as real taste signal.</p>
            </div>

            <div className="feedbackGrid">
              {participantEntries.map((participant) => (
                <article key={participant.id} className="feedbackCard">
                  <h4>{participant.label}</h4>
                  <div className="outcomeOptionGrid" role="group" aria-label={`${participant.label} feedback`}>
                    {(Object.keys(feedbackLabels) as Array<keyof typeof feedbackLabels>).map((label) => (
                      <button
                        key={label}
                        type="button"
                        className={feedbackState[participant.id] === label ? "segment segmentActive" : "segment"}
                        onClick={() => onFeedbackChange(participant.id, label)}
                      >
                        {feedbackLabels[label]}
                      </button>
                    ))}
                  </div>
                  <label className="noteField">
                    <span>Optional note</span>
                    <textarea
                      value={feedbackNotes[participant.id] ?? ""}
                      onChange={(event) => onFeedbackNoteChange(participant.id, event.target.value)}
                      rows={3}
                      placeholder={`Anything ${participant.label.toLowerCase()} wants remembered?`}
                    />
                  </label>
                </article>
              ))}
            </div>

            <div className="bottomActions inlineActions">
              <button
                type="button"
                className="primaryAction"
                onClick={onSaveFeedback}
                disabled={!feedbackReady}
              >
                {savedFeedbackCount === participantCount ? "Feedback saved" : "Save feedback"}
              </button>
            </div>
            {feedbackError ? <p className="debugMessage quietCallout">{feedbackError}</p> : null}
          </section>
        ) : null}
      </div>
    </details>
  );
}

export function SteerNextPanel({
  activeIntents,
  text,
  pendingIntent,
  referenceTitle,
  clarificationText,
  message,
  busy,
  canPersist,
  onTextChange,
  onInterpret,
  onClarificationTextChange,
  onAnswerClarification,
  onApply,
}: {
  activeIntents: TonightIntentInterpretationPayload[];
  text: string;
  pendingIntent: TonightIntentInterpretationPayload | null;
  referenceTitle?: string | null;
  clarificationText: string;
  message: string | null;
  busy: boolean;
  canPersist: boolean;
  onTextChange: (text: string) => void;
  onInterpret: () => void | Promise<void>;
  onClarificationTextChange: (text: string) => void;
  onAnswerClarification: () => void | Promise<void>;
  onApply: () => void | Promise<void>;
}) {
  const pendingSignals = pendingIntent?.softSignals.slice(0, 4) ?? [];
  const hasClarification = pendingIntent?.status === "clarification_required";
  const hasConfirmation = pendingIntent?.status === "confirmation_required";
  const quickSteers = [
    "different direction",
    referenceTitle ? `more like ${referenceTitle}` : "more like the winner",
    referenceTitle ? `avoid movies like ${referenceTitle}` : "avoid this direction",
  ];

  return (
    <section className="tonightIntentPanel steerNextPanel" aria-labelledby="steer-next-heading">
      <div className="tonightIntentHeader">
        <div>
          <p className="eyebrow">Steer next 5</p>
          <h3 id="steer-next-heading">Add one more tonight nudge</h3>
        </div>
      </div>

      {activeIntents.length > 0 ? (
        <div className="tonightIntentActive">
          <strong>Still active</strong>
          <div className="tonightIntentSignals">
            {activeIntents.map((intent, index) => (
              <span key={`${intent.rawText}-${index}`}>
                {intent.rawText}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <div className="tonightIntentComposer">
        <label htmlFor="steer-next-input">New steer</label>
        <div className="tonightIntentQuickActions">
          {quickSteers.map((quickSteer) => (
            <button
              key={quickSteer}
              type="button"
              className="secondaryButton compactButton"
              onClick={() => onTextChange(quickSteer)}
              disabled={busy || !canPersist}
            >
              {quickSteer}
            </button>
          ))}
        </div>
        <div className="tonightIntentInputRow">
          <input
            id="steer-next-input"
            value={text}
            onChange={(event) => onTextChange(event.target.value)}
            placeholder="actually more action"
            disabled={busy || !canPersist}
          />
          <button
            type="button"
            className="secondaryAction compactAction"
            onClick={onInterpret}
            disabled={busy || !canPersist || text.trim().length === 0}
          >
            Review
          </button>
        </div>
      </div>

      {hasConfirmation ? (
        <div className="tonightIntentReview">
          <p>{pendingIntent.confirmationText}</p>
          {pendingSignals.length > 0 ? (
            <div className="tonightIntentSignals">
              {pendingSignals.map((signal) => (
                <span key={`steer-${signal}`}>{formatTonightIntentSignal(signal)}</span>
              ))}
            </div>
          ) : null}
          <button
            type="button"
            className="primaryAction compactAction"
            onClick={onApply}
            disabled={busy || !canPersist}
          >
            Apply steer and show 5
          </button>
        </div>
      ) : null}

      {hasClarification ? (
        <div className="tonightIntentReview">
          <p>{pendingIntent.clarificationQuestion}</p>
          <div className="tonightIntentInputRow">
            <input
              value={clarificationText}
              onChange={(event) => onClarificationTextChange(event.target.value)}
              placeholder="comforting, not matching the mood"
              disabled={busy || !canPersist}
              aria-label="Clarify steer next 5"
            />
            <button
              type="button"
              className="secondaryAction compactAction"
              onClick={onAnswerClarification}
              disabled={busy || !canPersist || clarificationText.trim().length === 0}
            >
              Answer
            </button>
          </div>
        </div>
      ) : null}

      {message ? <p className="tonightIntentNote">{message}</p> : null}
    </section>
  );
}

export function RecommendationEvidencePanel({
  bestPick,
  activeIntents,
  participantEntries,
  tasteProfileSummaries,
}: {
  bestPick: RankedCandidate;
  activeIntents: TonightIntentInterpretationPayload[];
  participantEntries: ResultsParticipantEntry[];
  tasteProfileSummaries: TasteProfileSummaryPayload[];
}) {
  const matchedPersonNames = bestPick.matchedPersonNames?.slice(0, 3) ?? [];
  const profileRows = participantEntries.map((participant) => {
    const summary = tasteProfileSummaries.find(
      (profileSummary) => profileSummary.profileId === participant.id,
    );
    return {
      label: participant.label,
      evidenceCount: summary?.preferenceEvidenceCount ?? 0,
      ratingCount: summary?.ratingCount ?? 0,
    };
  });

  return (
    <section className="recommendationEvidencePanel" aria-labelledby="recommendation-evidence-heading">
      <div>
        <p className="eyebrow">Why these 5</p>
        <h3 id="recommendation-evidence-heading">Current signals</h3>
      </div>
      <div className="recommendationEvidenceGrid">
        <div>
          <strong>Tonight</strong>
          {activeIntents.length > 0 ? (
            <div className="tonightIntentSignals">
              {activeIntents.slice(0, 3).map((intent, index) => (
                <span key={`${intent.rawText}-${index}`}>{intent.rawText}</span>
              ))}
            </div>
          ) : (
            <p>No extra steer applied.</p>
          )}
        </div>
        <div>
          <strong>Taste Lab</strong>
          <div className="tonightIntentSignals">
            {profileRows.map((profileRow) => (
              <span key={profileRow.label}>
                {profileRow.label}: {profileRow.evidenceCount} signals
              </span>
            ))}
          </div>
        </div>
        <div>
          <strong>Best pick</strong>
          <p>
            {matchedPersonNames.length > 0
              ? `Matched ${matchedPersonNames.join(", ")}.`
              : `${bestPick.title} led the shared score.`}
          </p>
        </div>
      </div>
    </section>
  );
}

export function SessionEvidencePanel({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <details className="disclosurePanel">
      <summary>Session evidence</summary>
      <div className="disclosureBody">{children}</div>
    </details>
  );
}

export function DebugHistoryPanel({
  source,
  session,
  history,
  tasteProfileSummaries,
  status,
  message,
  onLoad,
}: {
  source: SessionSource;
  session: SharedSessionPayload | null;
  history: DebugHistorySessionPayload | null;
  tasteProfileSummaries: TasteProfileSummaryPayload[];
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
            <div>
              <dt>Batches</dt>
              <dd>{history.batchCount}</dd>
            </div>
            <div>
              <dt>Shown titles</dt>
              <dd>{history.shownSourceMovieIds.length}</dd>
            </div>
          </dl>

          <DebugList
            label="Previous batch"
            items={history.previousShortlist.map(
              (item) => `${item.title} (${item.sourceMovieId})`,
            )}
          />

          <DebugList
            label="Session outcome"
            items={
              history.sessionOutcome
                ? [
                    [
                      history.sessionOutcome.outcomeType,
                      history.sessionOutcome.selectedTitle,
                      history.sessionOutcome.selectionOrigin,
                      history.sessionOutcome.hasNotes ? "notes saved" : null,
                    ]
                      .filter(Boolean)
                      .join(" · "),
                  ]
                : []
            }
          />

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
          <DebugReactionList
            label="Previous founder reactions"
            reactions={history.previousFounderReactions}
          />
          <DebugReactionList
            label="Previous wife reactions"
            reactions={history.previousWifeReactions}
          />
          <DebugList
            label="Post-watch feedback"
            items={history.postWatchFeedback.map(
              (feedback) =>
                `${feedback.userId}: ${feedback.sourceMovieId} = ${feedback.feedbackLabel}${
                  feedback.hasFreeTextNote ? " (note)" : ""
                }`,
            )}
          />
          <DebugTasteProfileSignals summaries={tasteProfileSummaries} />
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

function DebugTasteProfileSignals({
  summaries,
}: {
  summaries: TasteProfileSummaryPayload[];
}) {
  return (
    <div className="debugListBlock">
      <h4>Taste profile signals</h4>
      {summaries.length > 0 ? (
        <div className="tasteProfileEvidenceGrid">
          {summaries.map((summary) => {
            const topSignals = summary.genreSignals.slice(0, 3);

            return (
              <article key={summary.profileId} className="tasteProfileEvidenceCard">
                <div>
                  <strong>{summary.profileId}</strong>
                  <span>
                    {summary.preferenceEvidenceCount} taste signals · {summary.familiarityOnlyCount} familiarity only
                  </span>
                </div>
                {topSignals.length > 0 ? (
                  <ol>
                    {topSignals.map((signal) => (
                      <li key={signal.genre}>
                        {signal.genre}: {formatTasteSignalScore(signal.score)}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p>No Taste Lab preference evidence saved yet.</p>
                )}
              </article>
            );
          })}
        </div>
      ) : (
        <p>No Taste Lab profile summary loaded yet.</p>
      )}
    </div>
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
      <DebugCandidateInputs candidateInputs={snapshot.candidateInputs} />
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

function DebugCandidateInputs({
  candidateInputs,
}: {
  candidateInputs: DebugHistoryCandidateInputPayload[];
}) {
  return (
    <div className="debugListBlock">
      <h4>Candidate inputs</h4>
      {candidateInputs.length > 0 ? (
        <ol>
          {candidateInputs.map((candidate) => (
            <li key={candidate.sourceMovieId}>
              {formatDebugCandidateInput(candidate)}
            </li>
          ))}
        </ol>
      ) : (
        <p>No candidate input snapshot saved yet.</p>
      )}
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

function formatTonightIntentSignal(signal: string): string {
  return signal
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatTasteSignalScore(score: number): string {
  if (score > 0) {
    return `+${score}`;
  }

  return String(score);
}

function HeartPulseIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <path d="M24 37.6 13.2 27.7C7.4 22.4 5 15.9 10.2 12.3c3.8-2.6 8.5-.8 10.7 2.6L24 19.1l3.1-4.2c2.2-3.4 6.9-5.2 10.7-2.6 5.2 3.6 2.8 10.1-3 15.4L24 37.6Z" />
    </svg>
  );
}

function RedoIcon() {
  return (
    <svg className="buttonIcon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4.8 8.2A8 8 0 1 1 4 12.7" />
      <path d="M4.8 8.2V4.4" />
      <path d="M4.8 8.2h4" />
    </svg>
  );
}

function BookmarkIcon() {
  return (
    <svg className="buttonIcon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 4.8c0-1 .8-1.8 1.8-1.8h6.4c1 0 1.8.8 1.8 1.8v15.1l-5-3.1-5 3.1V4.8Z" />
    </svg>
  );
}
