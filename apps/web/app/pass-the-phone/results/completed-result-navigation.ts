export type CompletedResultNavigationActions = {
  home: {
    ariaLabel: string;
    activate: () => void;
  };
  newNight: {
    label: string;
    activate: () => void;
  };
};

/**
 * Both result-stage exit controls start the same clean session flow.
 * Keeping the controls together prevents their visible labels from drifting
 * away from the navigation behavior they expose.
 */
export function completedResultNavigationActions(
  onRestart: () => void,
): CompletedResultNavigationActions {
  return {
    home: {
      ariaLabel: "WatchSignal home, start a new night",
      activate: onRestart,
    },
    newNight: {
      label: "New night",
      activate: onRestart,
    },
  };
}
