"use client";

import { useEffect, useState } from "react";
import { toErrorMessage } from "../../pass-the-phone-helpers";
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

type WatchlistStatus = "idle" | "loading" | "saving" | "removing" | "marking";

type ResultsPersistenceOptions = {
  sessionSource: SessionSource;
  sharedSession: SharedSessionPayload | null;
  participantIds: string[];
  participantEntries: ResultsParticipantEntry[];
  rankedCandidates: RankedCandidate[];
  bestPick: RankedCandidate | undefined;
  onLoadDebugHistory: () => void | Promise<void>;
  onRefreshProfileMemory: () => void | Promise<void>;
};

export function useResultsPersistence({
  sessionSource,
  sharedSession,
  participantIds,
  participantEntries,
  rankedCandidates,
  bestPick,
  onLoadDebugHistory,
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
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [watchlistEntries, setWatchlistEntries] = useState<WatchlistEntryPayload[]>([]);
  const [watchlistStatus, setWatchlistStatus] = useState<WatchlistStatus>("idle");
  const [watchlistMessage, setWatchlistMessage] = useState<string | null>(null);
  const [watchlistRatingState, setWatchlistRatingState] = useState<
    Record<string, Record<string, "loved" | "fine" | "no">>
  >({});

  const householdId = sharedSession?.householdId ?? "default-household";
  const canPersist = sessionSource === "api" && sharedSession !== null;
  const canShowMore = sessionSource === "api";
  const canSaveWatchlist = sessionSource === "api";

  useEffect(() => {
    if (!canSaveWatchlist) {
      setWatchlistEntries([]);
      setWatchlistMessage(null);
      return;
    }

    void refreshWatchlist();
  }, [canSaveWatchlist, householdId]);

  const watchedTitleSourceId =
    savedOutcome?.selectedSourceMovieId ??
    (outcomeType === "watched_recommended"
      ? bestPick?.id ?? null
      : outcomeType === "watched_other"
        ? otherPickId
        : null);
  const watchedTitle =
    watchedTitleSourceId !== null
      ? rankedCandidates.find(
          (candidate) => candidate.id === watchedTitleSourceId,
        ) ?? null
      : null;
  const canSaveOutcome =
    canPersist &&
    outcomeType !== null &&
    (outcomeType !== "watched_other" || otherPickId !== null);
  const feedbackReady =
    watchedTitleSourceId !== null &&
    participantIds.every(
      (participantId) => feedbackState[participantId] !== undefined,
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
    setOutcomeError(null);
    setFeedbackError(null);
  }

  function handleOtherPickChange(sourceMovieId: string): void {
    setOtherPickId(sourceMovieId);
    setSavedOutcome(null);
    setSavedFeedback([]);
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
    setFeedbackState((current) => ({
      ...current,
      [participantId]: feedback,
    }));
    setFeedbackError(null);
  }

  function handleFeedbackNoteChange(participantId: string, note: string): void {
    setFeedbackNotes((current) => ({
      ...current,
      [participantId]: note,
    }));
    setFeedbackError(null);
  }

  function handleWatchlistRatingChange(
    sourceMovieId: string,
    profileId: string,
    rating: "loved" | "fine" | "no",
  ): void {
    setWatchlistRatingState((current) => ({
      ...current,
      [sourceMovieId]: {
        ...(current[sourceMovieId] ?? {}),
        [profileId]: rating,
      },
    }));
  }

  async function refreshWatchlist(): Promise<void> {
    if (!canSaveWatchlist) {
      return;
    }

    setWatchlistStatus("loading");
    try {
      const entries = await getWatchlist(householdId);
      setWatchlistEntries(entries);
      setWatchlistMessage(null);
    } catch (error) {
      setWatchlistMessage(toErrorMessage(error));
    } finally {
      setWatchlistStatus("idle");
    }
  }

  async function handleSaveBestPick(): Promise<void> {
    if (!canSaveWatchlist || !bestPick) {
      setWatchlistMessage("Watchlist saving needs the live backend connection.");
      return;
    }

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
      setWatchlistMessage(`${bestPick.title} is saved to your watchlist.`);
    } catch (error) {
      setWatchlistMessage(toErrorMessage(error));
    } finally {
      setWatchlistStatus("idle");
    }
  }

  async function handleRemoveWatchlistEntry(
    sourceMovieId: string,
  ): Promise<void> {
    if (!canSaveWatchlist) {
      return;
    }

    setWatchlistStatus("removing");
    try {
      await removeWatchlistEntry(householdId, sourceMovieId);
      setWatchlistEntries((currentEntries) =>
        currentEntries.filter((entry) => entry.sourceMovieId !== sourceMovieId),
      );
      setWatchlistMessage("Removed from your watchlist.");
    } catch (error) {
      setWatchlistMessage(toErrorMessage(error));
    } finally {
      setWatchlistStatus("idle");
    }
  }

  async function handleMarkWatchlistEntryWatched(
    entry: WatchlistEntryPayload,
  ): Promise<void> {
    if (!canPersist || sharedSession === null) {
      return;
    }

    setWatchlistStatus("marking");
    try {
      const ratings = Object.entries(
        watchlistRatingState[entry.sourceMovieId] ?? {},
      ).map(([profileId, tasteLabel]) => ({ profileId, tasteLabel }));
      await markAppOwnedMovieWatched({
        householdId: sharedSession.householdId,
        sourceMovieId: entry.sourceMovieId,
        title: entry.title,
        ratings,
      });
      setWatchlistMessage(
        `${entry.title} is marked watched${ratings.length ? " with ratings." : "."}`,
      );
      await onLoadDebugHistory();
    } catch (error) {
      setWatchlistMessage(toErrorMessage(error));
    } finally {
      setWatchlistStatus("idle");
    }
  }

  async function handleSaveOutcome(): Promise<void> {
    if (
      !canPersist ||
      sharedSession === null ||
      outcomeType === null ||
      !bestPick
    ) {
      return;
    }

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

    setOutcomeError(null);
    try {
      const outcome = await submitSessionOutcome(sharedSession.sessionId, payload);
      setSavedOutcome(outcome);
      setSavedFeedback([]);
      setFeedbackError(null);
      await onLoadDebugHistory();
    } catch (error) {
      setOutcomeError(toErrorMessage(error));
      console.error(error);
    }
  }

  async function handleSaveFeedback(): Promise<void> {
    if (
      !canPersist ||
      sharedSession === null ||
      watchedTitleSourceId === null ||
      !feedbackReady
    ) {
      return;
    }

    setFeedbackError(null);
    try {
      const feedback = await Promise.all(
        participantIds.map((participantId) =>
          submitPostWatchFeedback({
            householdId: sharedSession.householdId,
            sessionId: sharedSession.sessionId,
            userId: participantId,
            sourceMovieId: watchedTitleSourceId,
            feedbackLabel: feedbackState[participantId]!,
            freeTextNote: feedbackNotes[participantId]?.trim() || null,
          } satisfies SavePostWatchFeedbackRequest),
        ),
      );
      setSavedFeedback(feedback);
      await onLoadDebugHistory();
      await onRefreshProfileMemory();
    } catch (error) {
      setFeedbackError(toErrorMessage(error));
      console.error(error);
    }
  }

  return {
    canPersist,
    canShowMore,
    canSaveWatchlist,
    canSaveOutcome,
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
    watchlistRatingState,
    bestPickWatchlistEntry,
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
