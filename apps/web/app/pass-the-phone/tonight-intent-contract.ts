import type { TonightIntentInterpretationPayload } from "../session-client";

export type IntentSignalKind = "wanted" | "avoided";

export type IntentSignalChip = {
  id: string;
  kind: IntentSignalKind;
  value: string;
  label: string;
};

type IntentSignalRemoval =
  | { source: "soft"; value: string }
  | { source: "excluded"; value: string }
  | { source: "filter"; key: string; value?: unknown };

type RemovableIntentSignalChip = IntentSignalChip & {
  removals: IntentSignalRemoval[];
};

export type IntentRequestGuard = {
  sequence: number;
};

export type IntentRequestTicket = {
  sequence: number;
  text: string;
};

const uncertainMoodPattern = /\b(sad|down|rough day|bad day|depressed|miserable|ugh)\b/i;

export function beginIntentRequest(
  guard: IntentRequestGuard,
  text: string,
): IntentRequestTicket {
  guard.sequence += 1;
  return { sequence: guard.sequence, text: text.trim() };
}

export function invalidateIntentRequests(guard: IntentRequestGuard): void {
  guard.sequence += 1;
}

export function isIntentRequestCurrent(
  guard: IntentRequestGuard,
  ticket: IntentRequestTicket,
): boolean {
  return guard.sequence === ticket.sequence;
}

export function intentSignalChips(
  interpretation: TonightIntentInterpretationPayload | null,
): IntentSignalChip[] {
  if (!interpretation) return [];

  return allIntentSignalChips(interpretation)
    .slice(0, 4)
    .map(({ removals: _removals, ...chip }) => chip);
}

export function removeIntentSignal(
  interpretation: TonightIntentInterpretationPayload,
  chipId: string,
): TonightIntentInterpretationPayload {
  const visibleOnly = retainVisibleIntentSignals(interpretation);
  const chip = allIntentSignalChips(visibleOnly).find(
    (candidate) => candidate.id === chipId,
  );
  return chip ? applyIntentRemovals(visibleOnly, chip.removals) : visibleOnly;
}

export function retainVisibleIntentSignals(
  interpretation: TonightIntentInterpretationPayload,
): TonightIntentInterpretationPayload {
  const chips = allIntentSignalChips(interpretation);
  let visibleOnly = interpretation;

  for (const hiddenChip of chips.slice(4)) {
    visibleOnly = applyIntentRemovals(visibleOnly, hiddenChip.removals);
  }

  return {
    ...visibleOnly,
    softSignals: visibleOnly.softSignals.filter(
      (signal) => !nonUserFacingSignals.has(normalizeSignal(signal)),
    ),
  };
}

export function canConfirmTonightIntent(
  interpretation: TonightIntentInterpretationPayload | null,
): boolean {
  return Boolean(
    interpretation?.status === "confirmation_required" &&
      intentSignalChips(interpretation).length > 0,
  );
}

export function intentSummary(
  interpretation: TonightIntentInterpretationPayload | null,
): string {
  const chips = intentSignalChips(interpretation);
  if (chips.length === 0) return "Optional";
  return chips.slice(0, 2).map((chip) => chip.label).join(" · ");
}

export function uncertainIntentParts(text: string): {
  before: string;
  uncertain: string | null;
  after: string;
} {
  const match = uncertainMoodPattern.exec(text);
  if (!match || match.index === undefined) {
    return { before: text, uncertain: null, after: "" };
  }
  return {
    before: text.slice(0, match.index),
    uncertain: match[0],
    after: text.slice(match.index + match[0].length),
  };
}

export function intentPublicError(connected: boolean): string {
  return connected
    ? "Couldn’t read that right now. Your sentence is still here."
    : "You’re offline. Your sentence is still here for later.";
}

const nonUserFacingSignals = new Set([
  "open-ended",
  "tonight",
  "person-request",
  "franchise-request",
]);

function allIntentSignalChips(
  interpretation: TonightIntentInterpretationPayload,
): RemovableIntentSignalChip[] {
  const chips: RemovableIntentSignalChip[] = [];
  const handledFilterKeys = new Set<string>();
  const filters = interpretation.filters;
  const genres = stringFilterValues(filters.genres);
  const people = stringFilterValues(filters.people);

  for (const genre of genres) {
    addChip(
      chips,
      signalChip("wanted", genre, [
        { source: "filter", key: "genres", value: genre },
        { source: "soft", value: genre },
      ]),
    );
  }
  if (genres.length > 0) handledFilterKeys.add("genres");

  for (const person of people) {
    addChip(chips, {
      id: `wanted:person:${normalizeSignal(person)}`,
      kind: "wanted",
      value: person,
      label: `With ${person}`,
      removals: [
        { source: "filter", key: "people", value: person },
        { source: "soft", value: "person-request" },
      ],
    });
  }
  if (people.length > 0) handledFilterKeys.add("people");

  if (filters.release_year_min !== undefined || filters.release_year_max !== undefined) {
    const start = filters.release_year_min;
    const end = filters.release_year_max;
    const label = yearFilterLabel(start, end);
    addChip(chips, {
      id: `wanted:release-year:${String(start ?? "")}:${String(end ?? "")}`,
      kind: "wanted",
      value: label,
      label,
      removals: [
        { source: "filter", key: "release_year_min" },
        { source: "filter", key: "release_year_max" },
        ...interpretation.softSignals
          .filter((signal) => /^\d{4}s$/i.test(signal.trim()))
          .map((value): IntentSignalRemoval => ({ source: "soft", value })),
      ],
    });
    handledFilterKeys.add("release_year_min");
    handledFilterKeys.add("release_year_max");
  }

  if (filters.exclude_watched === true) {
    addChip(chips, {
      id: "wanted:not-seen",
      kind: "wanted",
      value: "not-seen",
      label: "Unseen only",
      removals: [
        { source: "filter", key: "exclude_watched" },
        { source: "soft", value: "not-seen" },
      ],
    });
    handledFilterKeys.add("exclude_watched");
  }

  if (filters.exclude_subtitled === true) {
    addChip(chips, {
      id: "avoided:subtitles",
      kind: "avoided",
      value: "subtitles",
      label: "No subtitles",
      removals: [
        { source: "filter", key: "exclude_subtitled" },
        { source: "excluded", value: "subtitles" },
      ],
    });
    handledFilterKeys.add("exclude_subtitled");
  }

  for (const [key, filterValue] of Object.entries(filters)) {
    if (handledFilterKeys.has(key) || filterValue === false || filterValue == null) continue;
    const values = Array.isArray(filterValue) ? filterValue : [filterValue];
    for (const value of values) {
      const normalizedValue = String(value).trim();
      if (!normalizedValue) continue;
      addChip(chips, {
        id: `wanted:filter:${key}:${normalizeSignal(normalizedValue)}`,
        kind: "wanted",
        value: normalizedValue,
        label: filterChipLabel(key, value),
        removals: [
          { source: "filter", key, value: Array.isArray(filterValue) ? value : undefined },
          { source: "soft", value: normalizedValue },
        ],
      });
    }
  }

  for (const signal of interpretation.softSignals) {
    const normalized = normalizeSignal(signal);
    if (nonUserFacingSignals.has(normalized)) continue;
    addChip(
      chips,
      signalChip("wanted", signal, [{ source: "soft", value: signal }]),
    );
  }

  for (const signal of interpretation.excludedSignals ?? []) {
    addChip(
      chips,
      signalChip("avoided", signal, [{ source: "excluded", value: signal }]),
    );
  }

  return chips;
}

function signalChip(
  kind: IntentSignalKind,
  value: string,
  removals: IntentSignalRemoval[],
): RemovableIntentSignalChip {
  const normalized = value.trim();
  const words = normalized
    .split("-")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1));
  const label = `${kind === "avoided" ? "Not " : ""}${words.join(" ")}`;
  return {
    id: `${kind}:${normalizeSignal(normalized)}`,
    kind,
    value: normalized,
    label,
    removals,
  };
}

function addChip(
  chips: RemovableIntentSignalChip[],
  next: RemovableIntentSignalChip,
): void {
  const existing = chips.find((chip) => chip.id === next.id);
  if (!existing) {
    chips.push(next);
    return;
  }

  existing.removals = uniqueRemovals([...existing.removals, ...next.removals]);
}

function uniqueRemovals(removals: IntentSignalRemoval[]): IntentSignalRemoval[] {
  return Array.from(
    new Map(
      removals.map((removal) => [JSON.stringify(removal), removal]),
    ).values(),
  );
}

function applyIntentRemovals(
  interpretation: TonightIntentInterpretationPayload,
  removals: IntentSignalRemoval[],
): TonightIntentInterpretationPayload {
  let softSignals = [...interpretation.softSignals];
  let excludedSignals = [...(interpretation.excludedSignals ?? [])];
  const filters = { ...interpretation.filters };

  for (const removal of removals) {
    if (removal.source === "soft") {
      softSignals = softSignals.filter(
        (signal) => normalizeSignal(signal) !== normalizeSignal(removal.value),
      );
      continue;
    }
    if (removal.source === "excluded") {
      excludedSignals = excludedSignals.filter(
        (signal) => normalizeSignal(signal) !== normalizeSignal(removal.value),
      );
      continue;
    }

    const current = filters[removal.key];
    if (removal.value !== undefined && Array.isArray(current)) {
      const remaining = current.filter(
        (value) => normalizeSignal(String(value)) !== normalizeSignal(String(removal.value)),
      );
      if (remaining.length > 0) filters[removal.key] = remaining;
      else delete filters[removal.key];
    } else {
      delete filters[removal.key];
    }
  }

  return { ...interpretation, softSignals, excludedSignals, filters };
}

function stringFilterValues(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && Boolean(item.trim()))
    : [];
}

function normalizeSignal(value: string): string {
  return value.trim().toLocaleLowerCase();
}

function yearFilterLabel(start: unknown, end: unknown): string {
  if (typeof start === "number" && typeof end === "number") {
    if (start === end) return String(start);
    if (end - start === 9 && start % 10 === 0) return `${start}s`;
    return `${start}-${end}`;
  }
  return String(start ?? end ?? "Release year");
}

function filterChipLabel(key: string, value: unknown): string {
  const normalizedKey = key.toLocaleLowerCase();
  if (normalizedKey.includes("runtime") && typeof value === "number") {
    return normalizedKey.includes("max") ? `Under ${value} min` : `At least ${value} min`;
  }
  if (normalizedKey.includes("language")) {
    const language = languageDisplayName(String(value));
    return `Language: ${language}`;
  }
  const label = key
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
  return `${label}: ${String(value)}`;
}

function languageDisplayName(value: string): string {
  const normalized = value.trim().toLocaleLowerCase();
  return {
    fr: "French",
    de: "German",
    es: "Spanish",
    it: "Italian",
    ja: "Japanese",
    ko: "Korean",
  }[normalized] ?? value;
}
