import type { CandidateViewModel } from "../pass-the-phone-model";

export const REQUIRED_SHORTLIST_SIZE = 5;

export type ShortlistGenerationStage =
  | "finding"
  | "checking"
  | "preparing"
  | "local"
  | "failed";

export type ShortlistGenerationOutcome =
  | {
      status: "ready";
      movieSource: "live" | "local";
      persistenceSource: "shared" | "local";
    }
  | { status: "failed"; message: string };

export function exactUsableShortlist(
  candidates: CandidateViewModel[],
  excludedSourceMovieIds: string[] = [],
): CandidateViewModel[] | null {
  const excluded = new Set(excludedSourceMovieIds);
  const seen = new Set<string>();
  const usable = candidates.filter((candidate) => {
    const id = candidate.id.trim();
    const title = candidate.title.trim();
    if (!id || !title || excluded.has(id) || seen.has(id)) {
      return false;
    }
    seen.add(id);
    return true;
  });

  return usable.length === REQUIRED_SHORTLIST_SIZE ? usable : null;
}

export function selectExactUsableShortlist(
  candidates: CandidateViewModel[],
  excludedSourceMovieIds: string[] = [],
): CandidateViewModel[] | null {
  const excluded = new Set(excludedSourceMovieIds);
  const seen = new Set<string>();
  const selected: CandidateViewModel[] = [];
  for (const candidate of candidates) {
    const id = candidate.id.trim();
    if (!id || !candidate.title.trim() || excluded.has(id) || seen.has(id)) continue;
    seen.add(id);
    selected.push(candidate);
    if (selected.length === REQUIRED_SHORTLIST_SIZE) break;
  }
  return exactUsableShortlist(selected, excludedSourceMovieIds);
}

export function publicShortlistFailure(): string {
  return "We couldn’t make five fresh picks. Your setup is still here.";
}

export function localShortlistNotice(): string {
  return "Using five built-in picks. This round stays on this phone.";
}

export function savedFallbackShortlistNotice(): string {
  return "Using five built-in picks. Your private reactions will still be saved.";
}

export function liveLocalShortlistNotice(): string {
  return "These are live picks, but this round stays on this phone. Reactions are not saved.";
}
