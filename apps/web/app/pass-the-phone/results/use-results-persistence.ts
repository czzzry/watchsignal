"use client";

import { useEffect, useRef, useState } from "react";
import type {
  FeedbackNoteState,
  FeedbackState,
  RankedCandidate,
  SessionSource,
} from "../../pass-the-phone-model";
import {
  getWatchlist,
  markAppOwnedMovieWatched,
  removeWatchlistEntry,
  saveWatchlistEntry,
  submitPostWatchFeedback,
  submitSessionOutcome,
  type PostWatchFeedbackPayload,
  type SavePostWatchFeedbackRequest,
  type SaveSessionOutcomeRequest,
  type SessionOutcomePayload,
  type SessionOutcomeType,
  type SharedSessionPayload,
  type WatchlistEntryPayload,
} from "../../session-client";
import type { ResultsParticipantEntry } from "./results-panels";
import {
  beginWatchlistEntryAction,
  confirmWatchlistEntryWatched,
  finishWatchlistEntryAction,
  invalidateWatchlistEntryWatched,
  publicWatchlistMessage,
  validWatchlistRatings,
  watchlistEntryForMutation,
  type WatchlistEntryBusyState,
  type WatchlistWatchedState,
} from "./watchlist-contract";
import {
  createOutcomeSubmissionTransaction,
  feedbackDraftCanSave,
  feedbackDraftFingerprint,
  outcomeDraftCanSave,
  outcomeDraftFingerprint,
  pendingFeedbackProfileIds,
  publicOutcomeError,
  settlePendingFeedback,
  type FeedbackSavedFingerprints,
  type OutcomeSubmissionTransaction,
} from "./outcome-contract";
import type { createReviewDiagnosticRequests } from "../review-mode-contract";

type WatchlistStatus = "idle" | "loading" | "saving" | "removing" | "marking";

type ResultsPersistenceOptions = {
  sessionSource: SessionSource;
  sharedSession: SharedSessionPayload | null;
  participantIds: string[];
  participantEntries: ResultsParticipantEntry[];
  rankedCandidates: RankedCandidate[];
  bestPick: RankedCandidate | undefined;
  diagnosticRequests: Pick<
    ReturnType<typeof createReviewDiagnosticRequests>,
    "markWatched" | "outcome" | "feedback"
  >;
  onRefreshProfileMemory: () => void | Promise<void>;
};

export function useResultsPersistence({
  sessionSource,
  sharedSession,
  participantIds,
  participantEntries,
  rankedCandidates,
  bestPick,
  diagnosticRequests,
  onRefreshProfileMemory,
}: ResultsPersistenceOptions) {
  const [outcomeType, setOutcomeType] = useState<SessionOutcomeType | null>(null);
  const [otherPickId, setOtherPickId] = useState<string | null>(null);
  const [outcomeNote, setOutcomeNote] = useState("");
  const [savedOutcome, setSavedOutcome] = useState<SessionOutcomePayload | null>(null);
  const [outcomeError, setOutcomeError] = useState<string | null>(null);
  const [feedbackState, setFeedbackState] = useState<FeedbackState>({});
  const [feedbackNotes, setFeedbackNotes] = useState<FeedbackNoteState>({});
  const [savedFeedback, setSavedFeedback] = useState<PostWatchFeedbackPayload[]>([]);
  const [feedbackSavedFingerprints, setFeedbackSavedFingerprints] =
    useState<FeedbackSavedFingerprints>({});
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [watchlistEntries, setWatchlistEntries] = useState<WatchlistEntryPayload[]>([]);
  const [watchlistStatus, setWatchlistStatus] = useState<WatchlistStatus>("idle");
  const [watchlistMessage, setWatchlistMessage] = useState<string | null>(null);
  const [watchlistEntryBusy, setWatchlistEntryBusy] = useState<WatchlistEntryBusyState>({});
  const [watchlistWatchedState, setWatchlistWatchedState] = useState<WatchlistWatchedState>({});
  const [watchlistRatingState, setWatchlistRatingState] = useState<
    Record<string, Record<string, "loved" | "fine" | "no">>
  >({});
  const [outcomeBusy, setOutcomeBusy] = useState(false);
  const [confirmedOutcomeFingerprint, setConfirmedOutcomeFingerprint] =
    useState<string | null>(null);
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const watchlistActionLocks = useRef(new Set<string>());
  const outcomeTransactionRef = useRef<OutcomeSubmissionTransaction | null>(null);
  const outcomeTransaction = outcomeTransactionRef.current ??=
    createOutcomeSubmissionTransaction();
  const feedbackLock = useRef(false);

  const householdId = sharedSession?.householdId ?? "default-household";
  const canPersist = sessionSource === "api" && sharedSession !== null;
  const canSaveWatchlist = sessionSource === "api";

  useEffect(() => {
    if (!canSaveWatchlist) {
      setWatchlistEntries([]);
      setWatchlistMessage(null);
      return;
    }

    void refreshWatchlist();
  }, [canSaveWatchlist, householdId]);

  const watchedTitleSourceId = savedOutcome?.selectedSourceMovieId ?? null;
  const watchedTitle =
    watchedTitleSourceId !== null
      ? rankedCandidates.find(
          (candidate) => candidate.id === watchedTitleSourceId,
        ) ?? null
      : null;
  const outcomeDraft = { outcomeType, otherPickId, note: outcomeNote };
  const currentOutcomeFingerprint = sharedSession === null
    ? null
    : outcomeDraftFingerprint(
        sharedSession.sessionId,
        outcomeDraft,
        bestPick?.id ?? null,
      );
  const outcomeConfirmed = currentOutcomeFingerprint !== null &&
    confirmedOutcomeFingerprint === currentOutcomeFingerprint;
  const canSaveOutcome = outcomeDraftCanSave(
    outcomeDraft,
    bestPick?.id ?? null,
    canPersist,
    rankedCandidates.map((candidate) => candidate.id),
  ) && !outcomeConfirmed;
  const feedbackReady = feedbackDraftCanSave(
    watchedTitleSourceId,
    participantIds,
    feedbackState,
    feedbackNotes,
    feedbackSavedFingerprints,
  );
  const bestPickWatchlistEntry = bestPick
    ? watchlistEntries.find((entry) => entry.sourceMovieId === bestPick.id)
    : undefined;

  function handleOutcomeTypeChange(nextOutcomeType: SessionOutcomeType): void {
    setOutcomeType(nextOutcomeType);
    if (nextOutcomeType !== "watched_other") {
      setOtherPickId(null);
    }
    setSavedOutcome(null);
    setSavedFeedback([]);
    setFeedbackSavedFingerprints({});
    setOutcomeError(null);
    setFeedbackError(null);
  }

  function handleOtherPickChange(sourceMovieId: string): void {
    setOtherPickId(sourceMovieId);
    setSavedOutcome(null);
    setSavedFeedback([]);
    setFeedbackSavedFingerprints({});
    setOutcomeError(null);
    setFeedbackError(null);
  }

  function handleOutcomeNoteChange(note: string): void {
    setOutcomeNote(note);
    setOutcomeError(null);
  }

  function handleFeedbackChange(
    participantId: string,
    feedback: "loved" | "fine" | "no",
  ): void {
    if (!participantIds.includes(participantId)) {
      setFeedbackError("That profile is not part of this session.");
      return;
    }
    setFeedbackState((current) => ({
      ...current,
      [participantId]: feedback,
    }));
    setSavedFeedback((current) =>
      current.filter((item) => item.userId !== participantId),
    );
    setFeedbackSavedFingerprints((current) => {
      const next = { ...current };
      delete next[participantId];
      return next;
    });
    setFeedbackError(null);
  }

  function handleFeedbackNoteChange(participantId: string, note: string): void {
    if (!participantIds.includes(participantId)) {
      setFeedbackError("That profile is not part of this session.");
      return;
    }
    setFeedbackNotes((current) => ({
      ...current,
      [participantId]: note,
    }));
    setSavedFeedback((current) =>
      current.filter((item) => item.userId !== participantId),
    );
    setFeedbackSavedFingerprints((current) => {
      const next = { ...current };
      delete next[participantId];
      return next;
    });
    setFeedbackError(null);
  }

  function handleWatchlistRatingChange(
    sourceMovieId: string,
    profileId: string,
    rating: "loved" | "fine" | "no",
  ): void {
    if (!participantIds.includes(profileId)) {
      setWatchlistMessage("That profile is not part of this session.");
      return;
    }
    if (!watchlistEntryForMutation(watchlistEntries, householdId, sourceMovieId)) {
      setWatchlistMessage("That movie is no longer in this watchlist.");
      return;
    }
    setWatchlistRatingState((current) => ({
      ...current,
      [sourceMovieId]: {
        ...(current[sourceMovieId] ?? {}),
        [profileId]: rating,
      },
    }));
    setWatchlistWatchedState((current) =>
      invalidateWatchlistEntryWatched(current, sourceMovieId),
    );
  }

  async function refreshWatchlist(): Promise<void> {
    if (!canSaveWatchlist) {
      return;
    }

    setWatchlistStatus("loading");
    try {
      const entries = await getWatchlist(householdId);
      setWatchlistEntries(entries.filter((entry) => entry.householdId === householdId));
      setWatchlistMessage(null);
    } catch (error) {
      setWatchlistMessage(publicWatchlistMessage("failed"));
    } finally {
      setWatchlistStatus("idle");
    }
  }

  async function handleSaveBestPick(): Promise<void> {
    if (!canSaveWatchlist || !bestPick) {
      setWatchlistMessage(publicWatchlistMessage("local-only"));
      return;
    }

    if (watchlistActionLocks.current.has(`save:${bestPick.id}`)) return;
    watchlistActionLocks.current.add(`save:${bestPick.id}`);

    setWatchlistStatus("saving");
    try {
      const savedEntry = await saveWatchlistEntry({
        householdId,
        sourceMovieId: bestPick.id,
        title: bestPick.title,
        savedByProfileId: participantEntries[0]?.id ?? null,
        savedByDisplayLabel: participantEntries[0]?.label ?? null,
        posterUrl: bestPick.posterUrl,
        releaseYear: bestPick.year,
      });
      setWatchlistEntries((currentEntries) => [
        savedEntry,
        ...currentEntries.filter(
          (entry) => entry.sourceMovieId !== savedEntry.sourceMovieId,
        ),
      ]);
      setWatchlistMessage(publicWatchlistMessage("saved", bestPick.title));
    } catch (error) {
      setWatchlistMessage(publicWatchlistMessage("failed"));
    } finally {
      watchlistActionLocks.current.delete(`save:${bestPick.id}`);
      setWatchlistStatus("idle");
    }
  }

  async function handleRemoveWatchlistEntry(
    sourceMovieId: string,
  ): Promise<void> {
    if (!canSaveWatchlist) {
      setWatchlistMessage(publicWatchlistMessage("local-only"));
      return;
    }

    const entry = watchlistEntryForMutation(watchlistEntries, householdId, sourceMovieId);
    if (!entry || watchlistActionLocks.current.has(sourceMovieId)) {
      if (!entry) setWatchlistMessage("That movie is no longer in this watchlist.");
      return;
    }
    watchlistActionLocks.current.add(sourceMovieId);
    setWatchlistEntryBusy((current) =>
      beginWatchlistEntryAction(current, sourceMovieId, "removing") ?? current,
    );

    try {
      await removeWatchlistEntry(householdId, sourceMovieId);
      setWatchlistEntries((currentEntries) =>
        currentEntries.filter((entry) => entry.sourceMovieId !== sourceMovieId),
      );
      setWatchlistWatchedState((current) =>
        invalidateWatchlistEntryWatched(current, sourceMovieId),
      );
      setWatchlistMessage(publicWatchlistMessage("removed"));
    } catch (error) {
      setWatchlistMessage(publicWatchlistMessage("failed"));
    } finally {
      watchlistActionLocks.current.delete(sourceMovieId);
      setWatchlistEntryBusy((current) => finishWatchlistEntryAction(current, sourceMovieId));
    }
  }

  async function handleMarkWatchlistEntryWatched(
    entry: WatchlistEntryPayload,
  ): Promise<void> {
    if (!canPersist || sharedSession === null) {
      setWatchlistMessage(publicWatchlistMessage("local-only"));
      return;
    }

    const currentEntry = watchlistEntryForMutation(
      watchlistEntries,
      sharedSession.householdId,
      entry.sourceMovieId,
    );
    if (
      !currentEntry ||
      watchlistWatchedState[entry.sourceMovieId] ||
      watchlistActionLocks.current.has(entry.sourceMovieId)
    ) {
      if (!currentEntry) setWatchlistMessage("That movie is no longer in this watchlist.");
      return;
    }
    watchlistActionLocks.current.add(entry.sourceMovieId);
    setWatchlistEntryBusy((current) =>
      beginWatchlistEntryAction(current, entry.sourceMovieId, "marking") ?? current,
    );

    try {
      const ratings = validWatchlistRatings(
        watchlistRatingState[entry.sourceMovieId] ?? {},
        participantIds,
      );
      await markAppOwnedMovieWatched({
        householdId: sharedSession.householdId,
        sourceMovieId: entry.sourceMovieId,
        title: entry.title,
        ratings,
      });
      setWatchlistMessage(
        `${entry.title} is marked watched${ratings.length ? " with ratings." : "."}`,
      );
      setWatchlistWatchedState((current) =>
        confirmWatchlistEntryWatched(current, entry.sourceMovieId),
      );
      await diagnosticRequests.markWatched();
    } catch (error) {
      setWatchlistMessage(publicWatchlistMessage("failed"));
    } finally {
      watchlistActionLocks.current.delete(entry.sourceMovieId);
      setWatchlistEntryBusy((current) => finishWatchlistEntryAction(current, entry.sourceMovieId));
    }
  }

  async function handleSaveOutcome(): Promise<void> {
    if (
      !canSaveOutcome ||
      !canPersist ||
      sharedSession === null ||
      outcomeType === null ||
      !bestPick
    ) {
      return;
    }
    if (currentOutcomeFingerprint === null) return;

    const selectedCandidate =
      outcomeType === "watched_recommended"
        ? bestPick
        : outcomeType === "watched_other"
          ? rankedCandidates.find((candidate) => candidate.id === otherPickId) ??
            null
          : null;
    const payload: SaveSessionOutcomeRequest =
      outcomeType === "watched_nothing"
        ? {
            householdId: sharedSession.householdId,
            outcomeType,
            notes: outcomeNote || null,
          }
        : {
            householdId: sharedSession.householdId,
            outcomeType,
            selectedSourceMovieId: selectedCandidate?.id ?? null,
            selectedTitle: selectedCandidate?.title ?? null,
            selectionOrigin:
              outcomeType === "watched_recommended"
                ? "pick_for_us"
                : "reranked_shortlist",
            notes: outcomeNote || null,
          };

    const attempt = outcomeTransaction.start(
      currentOutcomeFingerprint,
      () => submitSessionOutcome(sharedSession.sessionId, payload),
    );
    if (attempt.status === "blocked") return;

    setOutcomeError(null);
    setOutcomeBusy(true);
    const result = await attempt.completion;
    if (result.status === "saved") {
      setSavedOutcome(result.value);
      setConfirmedOutcomeFingerprint(result.fingerprint);
      setSavedFeedback([]);
      setFeedbackSavedFingerprints({});
      setFeedbackError(null);
      void diagnosticRequests.outcome().catch(() => {});
    } else {
      setOutcomeError(publicOutcomeError("outcome"));
    }
    setOutcomeBusy(false);
  }

  async function handleSaveFeedback(): Promise<void> {
    if (
      !canPersist ||
      sharedSession === null ||
      savedOutcome === null ||
      watchedTitleSourceId === null ||
      !feedbackReady
    ) {
      return;
    }
    if (feedbackLock.current) return;
    feedbackLock.current = true;
    setFeedbackBusy(true);

    setFeedbackError(null);
    try {
      const pendingProfileIds = pendingFeedbackProfileIds(
        participantIds,
        feedbackState,
        feedbackNotes,
        feedbackSavedFingerprints,
      );
      const attempt = await settlePendingFeedback(
        pendingProfileIds,
        (participantId) => submitPostWatchFeedback({
            householdId: sharedSession.householdId,
            sessionId: sharedSession.sessionId,
            userId: participantId,
            sourceMovieId: watchedTitleSourceId,
            feedbackLabel: feedbackState[participantId]!,
            freeTextNote: feedbackNotes[participantId]?.trim() || null,
          } satisfies SavePostWatchFeedbackRequest),
      );
      const saved = attempt.saved.map(({ value }) => value);
      if (saved.length > 0) {
        setSavedFeedback((current) => [
          ...current.filter(
            (item) => !saved.some((next) => next.userId === item.userId),
          ),
          ...saved,
        ]);
        setFeedbackSavedFingerprints((current) => {
          const next = { ...current };
          for (const item of saved) {
            const fingerprint = feedbackDraftFingerprint(
              feedbackState[item.userId],
              feedbackNotes[item.userId],
            );
            if (fingerprint !== null) next[item.userId] = fingerprint;
          }
          return next;
        });
      }
      if (attempt.failedProfileIds.length > 0) {
        setFeedbackError(publicOutcomeError("feedback"));
        return;
      }
      await diagnosticRequests.feedback();
      await onRefreshProfileMemory();
    } catch (error) {
      setFeedbackError(publicOutcomeError("feedback"));
    } finally {
      feedbackLock.current = false;
      setFeedbackBusy(false);
    }
  }

  return {
    canPersist,
    canSaveWatchlist,
    canSaveOutcome,
    outcomeConfirmed,
    outcomeType,
    otherPickId,
    outcomeNote,
    savedOutcome,
    outcomeError,
    feedbackState,
    feedbackNotes,
    savedFeedback,
    feedbackSavedFingerprints,
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
  };
}
