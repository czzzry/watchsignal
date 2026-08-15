export const LOCAL_PRIVATE_TRANSITION_KEY = "watchsignal.local-private-transition.v1";

type LocalPrivateTransitionStorage = Pick<Storage, "getItem" | "removeItem" | "setItem">;

export function markLocalPrivateTransition(
  storage: LocalPrivateTransitionStorage,
): void {
  storage.setItem(LOCAL_PRIVATE_TRANSITION_KEY, "interrupted");
}

export function consumeLocalPrivateTransition(
  storage: LocalPrivateTransitionStorage,
): boolean {
  const interrupted = storage.getItem(LOCAL_PRIVATE_TRANSITION_KEY) === "interrupted";
  storage.removeItem(LOCAL_PRIVATE_TRANSITION_KEY);
  return interrupted;
}

export function clearLocalPrivateTransition(
  storage: LocalPrivateTransitionStorage,
): void {
  storage.removeItem(LOCAL_PRIVATE_TRANSITION_KEY);
}
