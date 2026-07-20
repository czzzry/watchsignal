import type { WizardStep } from "../pass-the-phone-model";


export type PassThePhoneNavigationState = {
  step: WizardStep;
};

export type PassThePhoneNavigationAction =
  | { type: "session.reset" }
  | { type: "session.started" }
  | { type: "founderPass.completed"; coupleSession: boolean }
  | { type: "handoff.completed" }
  | { type: "wifePass.completed" }
  | { type: "navigation.back" };

export const initialPassThePhoneNavigationState: PassThePhoneNavigationState = {
  step: "setup",
};

export function passThePhoneNavigationReducer(
  state: PassThePhoneNavigationState,
  action: PassThePhoneNavigationAction,
): PassThePhoneNavigationState {
  switch (action.type) {
    case "session.reset":
      return initialPassThePhoneNavigationState;
    case "session.started":
      return { step: "founder" };
    case "founderPass.completed":
      if (state.step !== "founder") {
        return state;
      }
      return { step: action.coupleSession ? "handoff" : "results" };
    case "handoff.completed":
      if (state.step !== "handoff") {
        return state;
      }
      return { step: "wife" };
    case "wifePass.completed":
      if (state.step !== "wife") {
        return state;
      }
      return { step: "results" };
    case "navigation.back":
      return { step: previousStep(state.step) };
  }
}

function previousStep(step: WizardStep): WizardStep {
  switch (step) {
    case "founder":
      return "setup";
    case "handoff":
      return "founder";
    case "wife":
      return "handoff";
    case "results":
      return "wife";
    case "setup":
      return "setup";
  }
}
