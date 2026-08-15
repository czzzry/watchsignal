import type {
  OnboardingCompletionPayload,
  ParticipantOnboardingPayload,
} from "../session-client.ts";
import type { OnboardingStatus } from "../pass-the-phone-model.ts";
import { onboardingHomeStatusCopy } from "./required-onboarding-contract.ts";
import { publicErrorMessage } from "./public-error-message.ts";

export type OnboardingTruthfulState = {
  status: OnboardingStatus;
  completion: OnboardingCompletionPayload | null;
  message: string | null;
};

export type OnboardingTruthfulPorts = {
  getCompletion: (
    requiredProfileIds: string[],
    signal?: AbortSignal,
  ) => Promise<OnboardingCompletionPayload>;
  saveProfile: (
    profileId: string,
    onboarding: ParticipantOnboardingPayload,
  ) => Promise<ParticipantOnboardingPayload>;
};

export type OnboardingSaveResult =
  | { status: "saved"; onboarding: ParticipantOnboardingPayload }
  | { status: "failed"; message: string };

export type OnboardingTruthfulController = {
  getSnapshot: () => OnboardingTruthfulState;
  subscribe: (listener: () => void) => () => void;
  check: (
    requiredProfileIds: string[],
  ) => Promise<OnboardingCompletionPayload | null>;
  save: (
    profileId: string,
    onboarding: ParticipantOnboardingPayload,
  ) => Promise<OnboardingSaveResult>;
  disconnect: () => void;
  cancelPending: () => void;
};

export function createOnboardingTruthfulController(
  ports: OnboardingTruthfulPorts,
  options: { initialStatus?: OnboardingStatus } = {},
): OnboardingTruthfulController {
  let state: OnboardingTruthfulState = {
    status: options.initialStatus ?? "idle",
    completion: null,
    message: null,
  };
  let operation = 0;
  let activeCheck: AbortController | null = null;
  const listeners = new Set<() => void>();

  function transition(next: OnboardingTruthfulState): void {
    state = next;
    listeners.forEach((listener) => listener());
  }

  function cancelPending(): void {
    operation += 1;
    activeCheck?.abort();
    activeCheck = null;
  }

  async function check(
    requiredProfileIds: string[],
  ): Promise<OnboardingCompletionPayload | null> {
    cancelPending();
    const currentOperation = operation;
    const abortController = new AbortController();
    activeCheck = abortController;
    transition({
      status: "loading",
      completion: state.completion,
      message: null,
    });

    try {
      const completion = await ports.getCompletion(
        requiredProfileIds,
        abortController.signal,
      );
      if (currentOperation !== operation) {
        return null;
      }
      activeCheck = null;
      transition({ status: "ready", completion, message: null });
      return completion;
    } catch (error) {
      if (currentOperation !== operation) {
        return null;
      }
      activeCheck = null;
      transition({
        status: "failed",
        completion: null,
        message: publicErrorMessage("onboarding-load", error),
      });
      return null;
    }
  }

  async function save(
    profileId: string,
    onboarding: ParticipantOnboardingPayload,
  ): Promise<OnboardingSaveResult> {
    cancelPending();
    const currentOperation = operation;
    transition({
      status: "saving",
      completion: state.completion,
      message: null,
    });

    try {
      const saved = await ports.saveProfile(profileId, onboarding);
      if (currentOperation !== operation) {
        return { status: "saved", onboarding: saved };
      }
      transition({ status: "ready", completion: state.completion, message: null });
      return { status: "saved", onboarding: saved };
    } catch (error) {
      const message = publicErrorMessage("onboarding-save", error);
      if (currentOperation === operation) {
        transition({
          status: "failed",
          completion: state.completion,
          message,
        });
      }
      return { status: "failed", message };
    }
  }

  return {
    getSnapshot: () => state,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    check,
    save,
    disconnect: () => {
      cancelPending();
      transition({ status: "ready", completion: null, message: null });
    },
    cancelPending,
  };
}

export function onboardingHomePresentation({
  state,
  onboardingRequired,
  onboardingPromptLabel,
  isSyncing,
  isCoupleSession,
}: {
  state: OnboardingTruthfulState;
  onboardingRequired: boolean;
  onboardingPromptLabel: string | null;
  isSyncing: boolean;
  isCoupleSession: boolean;
}): {
  busyLabel: "Checking" | "Saving" | null;
  progressLabel: string;
  completionKnown: boolean;
  primaryLabel: string;
  primaryDisabled: boolean;
} {
  const completedCount = state.completion?.completedProfileIds.length ?? 0;
  const totalCount = state.completion?.requiredProfileIds.length ?? (isCoupleSession ? 2 : 1);
  const copy = onboardingHomeStatusCopy(
    state.status,
    state.completion ? completedCount : null,
    totalCount,
  );
  return {
    ...copy,
    primaryLabel: onboardingRequired
      ? onboardingPromptLabel
        ? `Continue ${onboardingPromptLabel}'s setup`
        : completedCount === 0
          ? "Set up tastes"
          : "Finish setup"
      : isSyncing
        ? "Building tonight's picks..."
        : "Start first pass",
    primaryDisabled: onboardingRequired
      ? state.status === "loading" || state.status === "saving"
      : isSyncing,
  };
}
