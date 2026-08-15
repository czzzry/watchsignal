import type {
  ProfileMemorySummaryPayload,
  TasteMemoryEventPayload,
} from "../session-client";

export type ProfileMemoryConfidence = "learning" | "early" | "growing";

export type ProfileMemorySnapshot = {
  profileId: string;
  label: string;
  confidence: ProfileMemoryConfidence;
  headline: string;
  detail: string;
  likes: string[];
  avoids: string[];
  evidenceCount: number;
};

export function buildProfileMemorySnapshot(
  summary: ProfileMemorySummaryPayload,
  events: TasteMemoryEventPayload[],
  label: string,
): ProfileMemorySnapshot {
  const positiveLabels = new Map<string, number>();
  const avoidLabels = new Map<string, number>();
  const profileEvents = uniqueProfileEvents(summary.profileId, events);

  for (const signal of summary.signals) {
    if (signal.source === "private_calibration") {
      const positiveCount = signal.positiveCount ?? 0;
      const neutralCount = signal.neutralCount ?? 0;
      const negativeCount = signal.negativeCount ?? 0;
      if (positiveCount > negativeCount && positiveCount > neutralCount) {
        addWeightedLabel(positiveLabels, signal.label, positiveCount - negativeCount);
      } else if (negativeCount > positiveCount && negativeCount > neutralCount) {
        addWeightedLabel(avoidLabels, signal.label, negativeCount - positiveCount);
      }
    }
  }

  for (const event of profileEvents) {
    if (event.eventType === "seen_before") {
      continue;
    }
    const direction = eventDirection(event);
    if (direction === "neutral") continue;
    const target = direction === "negative" ? avoidLabels : positiveLabels;
    for (const genre of event.genres) {
      addWeightedLabel(target, genre, 1);
    }
  }

  const mixedLabels = new Set(
    [...positiveLabels.keys()].filter((genre) => avoidLabels.has(genre)),
  );
  for (const genre of mixedLabels) {
    positiveLabels.delete(genre);
    avoidLabels.delete(genre);
  }
  const likes = topLabels(positiveLabels, 2);
  const avoids = topLabels(avoidLabels, 2);
  const hasMixedEvidence = mixedLabels.size > 0;
  const summaryEvidenceCount = Math.max(
    summary.visibleAppMemoryCount,
    summary.privateCalibrationCount,
  );
  const eventEvidenceCount = profileEvents.filter(
    (event) => event.eventType !== "seen_before",
  ).length;
  const evidenceCount = Math.max(summaryEvidenceCount, eventEvidenceCount);
  const confidence: ProfileMemoryConfidence =
    evidenceCount >= 8 ? "growing" : evidenceCount >= 3 ? "early" : "learning";

  return {
    profileId: summary.profileId,
    label,
    confidence,
    headline:
      hasMixedEvidence
        ? "Still taking shape"
        : confidence === "growing" && likes.length > 0
        ? `Leaning toward ${likes.join(" and ")}`
        : confidence === "early" && likes.length > 0
          ? `Early signal for ${likes[0]}`
          : confidence === "growing" && avoids.length > 0
            ? `Clearer boundary around ${avoids[0]}`
            : confidence === "early" && avoids.length > 0
              ? `Early boundary around ${avoids[0]}`
              : confidence === "learning"
                ? "Still learning"
                : "Still taking shape",
    detail:
      hasMixedEvidence
        ? `Mixed signals around ${topMixedLabels(mixedLabels)}.`
        : confidence === "learning"
        ? "A few more choices will make this clearer."
        : avoids.length > 0
          ? `Possible avoids: ${avoids.join(" and ")}.`
          : "No reliable avoid yet.",
    likes,
    avoids,
    evidenceCount,
  };
}

function uniqueProfileEvents(
  profileId: string,
  events: TasteMemoryEventPayload[],
): TasteMemoryEventPayload[] {
  const unique = new Map<string, TasteMemoryEventPayload>();
  for (const event of events) {
    if (event.profileId === profileId && !unique.has(event.eventId)) {
      unique.set(event.eventId, event);
    }
  }
  return [...unique.values()];
}

export function householdMemorySummary(
  snapshots: ProfileMemorySnapshot[],
): string {
  if (snapshots.length < 2 || snapshots.some((snapshot) => snapshot.confidence === "learning")) {
    return "Still learning your shared taste";
  }

  const [first, second] = snapshots;
  const overlap = first.likes.filter((label) => second.likes.includes(label));
  return overlap.length > 0
    ? `Early overlap around ${overlap.slice(0, 2).join(" and ")}`
    : "Distinct signals so far";
}

export function profileMemoryPublicMessage(
  status: "loading" | "ready" | "failed",
  message: string | null,
): string | null {
  if (status === "loading") return "Reading taste memory…";
  if (status === "failed") return message ?? "Couldn’t load taste memory. Try again.";
  return null;
}

function eventDirection(
  event: TasteMemoryEventPayload,
): "positive" | "neutral" | "negative" {
  const sentiment = event.sentimentLabel?.trim().toLocaleLowerCase();
  if (sentiment === "no" || sentiment === "hated") return "negative";
  if (sentiment === "loved" || sentiment === "liked" || sentiment === "interested") {
    return "positive";
  }
  return "neutral";
}

function addWeightedLabel(labels: Map<string, number>, label: string, weight: number): void {
  const normalized = label.trim();
  if (!normalized) return;
  labels.set(normalized, (labels.get(normalized) ?? 0) + weight);
}

function topLabels(labels: Map<string, number>, limit: number): string[] {
  return [...labels.entries()]
    .sort((first, second) => second[1] - first[1] || first[0].localeCompare(second[0]))
    .slice(0, limit)
    .map(([label]) => label);
}

function topMixedLabels(labels: Set<string>): string {
  return [...labels].sort((first, second) => first.localeCompare(second)).slice(0, 2).join(" and ");
}
