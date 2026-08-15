import type {
  HouseholdHistoryDetailPayload,
  HouseholdHistorySummaryPayload,
} from "../session-client";

export function historyDateLabel(value: string | null): string {
  if (!value) return "Date unavailable";
  const normalized = /Z$|[+-]\d\d:\d\d$/.test(value) ? value : `${value.replace(" ", "T")}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.valueOf())) return "Date unavailable";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function recentNightSummary(session: HouseholdHistorySummaryPayload): {
  title: string;
  outcome: string;
  date: string;
} {
  return {
    title: session.title,
    outcome: session.outcomeLabel,
    date: historyDateLabel(session.occurredAt),
  };
}

export function householdHistoryDetail(history: HouseholdHistoryDetailPayload): {
  chosenTitle: string;
  posterUrl: string | null;
  alternatives: Array<{ title: string; posterUrl: string | null }>;
  outcome: string;
  feedback: string[];
} {
  return {
    chosenTitle: history.title,
    posterUrl: history.posterUrl,
    alternatives: history.alternatives.map((movie) => ({
      title: movie.title,
      posterUrl: movie.posterUrl ?? null,
    })),
    outcome: history.outcomeLabel,
    feedback: history.feedbackLabels,
  };
}

export function historyPublicMessage(
  status: "idle" | "loading" | "ready" | "failed",
  message: string | null,
): string | null {
  if (status === "loading") return "Loading recent nights…";
  if (status === "failed") {
    if (/connect|offline|unavailable/i.test(message ?? "")) {
      return "Recent nights aren’t available offline. Nothing was changed.";
    }
    return "Couldn’t load recent nights. Try again.";
  }
  return null;
}
