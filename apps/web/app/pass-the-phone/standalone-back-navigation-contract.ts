export const standaloneBackGuardStateKey = "__watchsignalStandaloneBackGuard";

export type StandaloneBackHistoryPort = {
  readonly state: unknown;
  pushState: (data: unknown, unused: string) => void;
};

export type StandaloneBackNavigationController = {
  start: () => void;
  stop: () => void;
};

export type StandaloneWizardBackAction =
  | "stay"
  | "close-overlay"
  | "previous-card"
  | "handoff"
  | "home";

export type StandaloneSurfaceBackAction = "stay" | "previous" | "close";

export type StandaloneWizardRecoveryStage =
  | "handoff_pending"
  | "handoff_ready"
  | "handoff_retry"
  | "second_pass_ready"
  | "matching_pending"
  | "matching_failed"
  | "sealing"
  | null;

export type StandaloneHandoffContinueAction =
  | "stay"
  | "resume-handoff"
  | "open-second-pass"
  | "reopen-second-pass"
  | "reject-unverified"
  | "advance-local";

export function standaloneSurfaceBackAction(input: {
  blocked: boolean;
  hasPrevious: boolean;
}): StandaloneSurfaceBackAction {
  if (input.blocked) return "stay";
  return input.hasPrevious ? "previous" : "close";
}

export function standaloneWizardRecoveryBlocksBack(
  stage: StandaloneWizardRecoveryStage,
): boolean {
  return stage === "sealing"
    || stage === "handoff_pending"
    || stage === "matching_pending";
}

export function standaloneHandoffContinueAction(input: {
  recoveryStage: StandaloneWizardRecoveryStage;
  apiSession: boolean;
}): StandaloneHandoffContinueAction {
  if (input.recoveryStage === "handoff_retry") return "resume-handoff";
  if (input.recoveryStage === "handoff_ready") return "open-second-pass";
  if (input.recoveryStage === "second_pass_ready") return "reopen-second-pass";
  if (standaloneWizardRecoveryBlocksBack(input.recoveryStage)) return "stay";
  if (input.recoveryStage === "matching_failed") return "stay";
  return input.apiSession ? "reject-unverified" : "advance-local";
}

export function standaloneWizardBackAction(input: {
  blocked: boolean;
  dismissibleOverlay: boolean;
  step: "setup" | "founder" | "handoff" | "wife" | "results";
  cardIndex: number;
}): StandaloneWizardBackAction {
  if (input.blocked) return "stay";
  if (input.dismissibleOverlay) return "close-overlay";
  if (input.step === "setup") return "stay";
  if (input.step === "handoff" || input.step === "results") return "home";
  if (input.cardIndex > 0) return "previous-card";
  return input.step === "wife" ? "handoff" : "home";
}

export type StandaloneBackHandlerRegistry = {
  register: (handler: () => void, priority: number) => () => void;
  handleBack: () => boolean;
};

export function createStandaloneBackHandlerRegistry(): StandaloneBackHandlerRegistry {
  let order = 0;
  const handlers = new Map<symbol, {
    handler: () => void;
    priority: number;
    order: number;
  }>();

  return {
    register(handler, priority) {
      const id = Symbol("standalone-back-handler");
      handlers.set(id, { handler, priority, order: order++ });
      return () => handlers.delete(id);
    },
    handleBack() {
      const active = [...handlers.values()].sort(
        (left, right) => right.priority - left.priority || right.order - left.order,
      )[0];
      if (!active) return false;
      active.handler();
      return true;
    },
  };
}

export function createStandaloneBackNavigationController(input: {
  standalone: boolean;
  history: StandaloneBackHistoryPort;
  listen: (listener: () => void) => () => void;
  onBack: () => void;
}): StandaloneBackNavigationController {
  let removeListener: (() => void) | null = null;

  function hasGuard(state: unknown): boolean {
    return Boolean(
      state &&
      typeof state === "object" &&
      standaloneBackGuardStateKey in state &&
      (state as Record<string, unknown>)[standaloneBackGuardStateKey] === true,
    );
  }

  function arm(): boolean {
    if (hasGuard(input.history.state)) return true;
    try {
      const currentState = input.history.state;
      const nextState = currentState && typeof currentState === "object"
        ? { ...currentState, [standaloneBackGuardStateKey]: true }
        : { [standaloneBackGuardStateKey]: true };
      input.history.pushState(nextState, "");
      return true;
    } catch {
      return false;
    }
  }

  function handlePopState(): void {
    try {
      input.onBack();
    } finally {
      arm();
    }
  }

  return {
    start() {
      if (!input.standalone || removeListener) return;
      if (!arm()) return;
      removeListener = input.listen(handlePopState);
    },
    stop() {
      removeListener?.();
      removeListener = null;
    },
  };
}
