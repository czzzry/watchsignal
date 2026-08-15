export const launchStingStorageKey = "watchsignal.launch-sting.v1";
export const launchStingMaximumMs = 900;

export type LaunchStingPlan = {
  show: boolean;
  durationMs: number;
  markAsSeen: boolean;
};

export function launchStingPlan({
  alreadyShown,
  reducedMotion,
}: {
  alreadyShown: boolean;
  reducedMotion: boolean;
}): LaunchStingPlan {
  if (alreadyShown || reducedMotion) {
    return {
      show: false,
      durationMs: 0,
      markAsSeen: !alreadyShown,
    };
  }

  return {
    show: true,
    durationMs: launchStingMaximumMs,
    markAsSeen: true,
  };
}
