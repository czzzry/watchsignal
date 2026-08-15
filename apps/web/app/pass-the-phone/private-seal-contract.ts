import type { WizardStep } from "../pass-the-phone-model";

export const PRIVACY_SEAL_DURATION_MS = 520;
export const PRIVACY_SEAL_MAX_MS = 650;

export type PrivacySealCompletionController = {
  complete(): void;
  dispose(): void;
};

export function createPrivacySealCompletionController<TimerToken>(
  onComplete: () => void,
  schedule: (callback: () => void, delayMs: number) => TimerToken,
  cancel: (token: TimerToken) => void,
): PrivacySealCompletionController {
  let completed = false;
  let scheduled = false;
  let timerToken: TimerToken;

  const complete = (): void => {
    if (completed) return;
    completed = true;
    if (scheduled) cancel(timerToken);
    onComplete();
  };

  timerToken = schedule(complete, PRIVACY_SEAL_MAX_MS);
  scheduled = true;

  return {
    complete,
    dispose(): void {
      if (completed) return;
      completed = true;
      cancel(timerToken);
    },
  };
}

export type PrivacySealCopy = {
  title: string;
  detail: string;
};

export function privacySealCopy(
  ownerLabel: string,
  localOnly = false,
): PrivacySealCopy {
  return {
    title: "Sealing your picks",
    detail: localOnly
      ? `${ownerLabel}'s answers stay private. Keep this tab open while we finish.`
      : `${ownerLabel}'s answers stay private.`,
  };
}

export function privateHandoffCopy(
  ownerLabel: string,
  recipientLabel: string,
): {
  title: string;
  detail: string;
  action: string;
} {
  return {
    title: `Ready for ${recipientLabel}`,
    detail: `${ownerLabel}'s picks are sealed. Only ${recipientLabel}'s choices appear next.`,
    action: `Begin ${recipientLabel}'s picks`,
  };
}

export function privacySafeBackTarget(step: WizardStep): WizardStep {
  return step === "handoff" ? "handoff" : step;
}

export function sealTransitionMeetsBudget(durationMs: number): boolean {
  return durationMs >= 0 && durationMs <= PRIVACY_SEAL_MAX_MS;
}
