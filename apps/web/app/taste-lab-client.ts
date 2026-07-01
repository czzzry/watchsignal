"use client";

export type TasteLabRatingLabel =
  | "loved"
  | "liked"
  | "meh"
  | "hated"
  | "havent_seen";

export type TasteLabMoviePayload = {
  sourceMovieId: string;
  title: string;
  releaseYear?: number | null;
  tmdbId?: string | null;
  posterPath?: string | null;
  genres: string[];
};

export type TasteLabQueueProvenancePayload = {
  queueSource: string;
  generatedAt?: string | null;
  rank?: number | null;
  signalScore?: number | null;
  scoreComponents: Record<string, number>;
};

export type TasteLabCandidatePayload = {
  movie: TasteLabMoviePayload;
  queueProvenance: TasteLabQueueProvenancePayload;
};

export type TasteLabRatingInputPayload = {
  movie: TasteLabMoviePayload;
  label: TasteLabRatingLabel;
  queueProvenance?: TasteLabQueueProvenancePayload | null;
  ratedAt?: string | null;
};

export type TasteLabRatingExportPayload = {
  schemaVersion: string;
  householdId: string;
  profileId: string;
  movie: TasteLabMoviePayload;
  label: TasteLabRatingLabel;
  familiarity: "seen" | "unseen";
  preferenceValue?: number | null;
  watchsignalTasteSignal: string;
  isImportablePreference: boolean;
  ratedAt: string;
  queueProvenance?: TasteLabQueueProvenancePayload | null;
};

export async function seedTasteLabCandidates(
  householdId: string,
  candidates: TasteLabCandidatePayload[],
): Promise<void> {
  const query = new URLSearchParams({ householdId });
  const response = await fetch(`/api/taste-lab/candidates?${query.toString()}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(candidates),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
}

export async function getTasteLabQueue(
  householdId: string,
  profileId: string,
  limit: number,
): Promise<TasteLabCandidatePayload[]> {
  const query = new URLSearchParams({
    householdId,
    limit: String(limit),
  });
  const response = await fetch(
    `/api/taste-lab/${encodeURIComponent(profileId)}/queue?${query.toString()}`,
    { method: "GET" },
  );

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  return (await response.json()) as TasteLabCandidatePayload[];
}

export async function submitTasteLabRatings(
  householdId: string,
  profileId: string,
  ratings: TasteLabRatingInputPayload[],
): Promise<TasteLabRatingExportPayload[]> {
  const response = await fetch(
    `/api/taste-lab/${encodeURIComponent(profileId)}/ratings`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ householdId, ratings }),
    },
  );

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  return (await response.json()) as TasteLabRatingExportPayload[];
}

export async function getTasteLabRatings(
  householdId: string,
  profileId: string,
): Promise<TasteLabRatingExportPayload[]> {
  const query = new URLSearchParams({ householdId });
  const response = await fetch(
    `/api/taste-lab/${encodeURIComponent(profileId)}/ratings?${query.toString()}`,
    { method: "GET" },
  );

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  return (await response.json()) as TasteLabRatingExportPayload[];
}

async function parseApiError(response: Response): Promise<string> {
  const payload = (await response.json().catch(() => null)) as unknown;

  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof payload.detail === "string"
  ) {
    return payload.detail;
  }

  return `Taste Lab API returned HTTP ${response.status}.`;
}
