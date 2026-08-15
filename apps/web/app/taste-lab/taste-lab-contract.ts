import type { TasteLabRatingLabel } from "../taste-lab-client";
import type { WatchSignalIconName } from "../ui/watchsignal-icons";

export type TasteLabQueueState =
  | "loading"
  | "ready"
  | "saving"
  | "batch-complete"
  | "empty"
  | "exhausted"
  | "error"
  | "local"
  | "local-exhausted";

export type TasteLabChoice = {
  value: TasteLabRatingLabel;
  label: string;
  icon: WatchSignalIconName;
};

export const tasteLabChoiceGroups: {
  preference: TasteLabChoice[];
  familiarity: TasteLabChoice;
} = {
  preference: [
    { value: "loved", label: "Loved", icon: "heart" },
    { value: "liked", label: "Liked it", icon: "thumbs-up" },
    { value: "meh", label: "It was fine", icon: "film" },
    { value: "hated", label: "Not for me", icon: "thumbs-down" },
  ],
  familiarity: { value: "havent_seen", label: "I haven’t seen it", icon: "eye-off" },
};

export function tasteLabLabelIsPreference(label: TasteLabRatingLabel): boolean {
  return label !== "havent_seen";
}

export function tasteLabQueueState(
  queueLength: number,
  historyLength: number,
  local: boolean,
): TasteLabQueueState {
  if (queueLength > 0) return local ? "local" : "ready";
  if (local) return "local-exhausted";
  return historyLength > 0 ? "exhausted" : "empty";
}
