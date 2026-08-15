import type { SeenMemoryValue } from "../pass-the-phone-model";
import type { WatchSignalIconName } from "../ui/watchsignal-icons";

export const seenMemoryValues = ["loved", "fine", "no", "forget"] as const satisfies readonly SeenMemoryValue[];

export const seenMemoryOptions: ReadonlyArray<{
  value: SeenMemoryValue;
  label: string;
  icon: WatchSignalIconName;
}> = [
  { value: "loved", label: "Loved", icon: "heart" },
  { value: "fine", label: "It was fine", icon: "thumbs-up" },
  { value: "no", label: "Not for me", icon: "thumbs-down" },
  { value: "forget", label: "I forget", icon: "history" },
];

export type SeenMemorySaveResult =
  | { status: "saved" | "local-only" }
  | { status: "failed"; message: string };

export function seenMemoryConfirmationLabel(localOnly: boolean): string {
  return localOnly ? "Seen on this phone" : "Seen saved";
}

export function canBeginSeenMemorySave({
  selected,
  saving,
  locked,
}: {
  selected: SeenMemoryValue | null;
  saving: boolean;
  locked: boolean;
}): boolean {
  return selected !== null && !saving && !locked;
}
