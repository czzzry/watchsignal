import {
  isolateModalBackground,
  restoreModalBackground,
  type ModalBackgroundSnapshot,
} from "../ui/accessible-modal-contract";

type IsolatedElement = {
  element: HTMLElement;
  snapshot: ModalBackgroundSnapshot | null;
};

export function isolateTransitionBackground(
  overlay: HTMLElement | null,
): () => void {
  if (!overlay?.parentElement) {
    return () => undefined;
  }

  const siblings = Array.from(overlay.parentElement.children).filter(
    (element): element is HTMLElement =>
      element instanceof HTMLElement && element !== overlay,
  );
  const externalTaskChrome = Array.from(
    document.querySelectorAll<HTMLElement>("body > .siteCreditsLink"),
  );
  const isolated: IsolatedElement[] = [...siblings, ...externalTaskChrome].map(
    (element) => ({
      element,
      snapshot: isolateModalBackground(element),
    }),
  );

  return () => {
    for (const { element, snapshot } of isolated) {
      restoreModalBackground(element, snapshot);
    }
  };
}
