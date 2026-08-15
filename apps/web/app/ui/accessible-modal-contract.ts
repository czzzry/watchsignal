export type FocusLoopDecision = "first" | "last" | "native" | "container";

export function focusLoopDecision({
  focusableCount,
  activeIndex,
  shiftKey,
}: {
  focusableCount: number;
  activeIndex: number;
  shiftKey: boolean;
}): FocusLoopDecision {
  if (focusableCount === 0) {
    return "container";
  }
  if (activeIndex < 0) {
    return shiftKey ? "last" : "first";
  }
  if (shiftKey && activeIndex <= 0) {
    return "last";
  }
  if (!shiftKey && activeIndex >= focusableCount - 1) {
    return "first";
  }
  return "native";
}

export const MODAL_FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "summary:not([tabindex='-1'])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export function modalTabStops(elements: HTMLElement[]): HTMLElement[] {
  return elements.filter(isModalTabStop);
}

export function isModalTabStop(element: HTMLElement): boolean {
  if (
    element.hasAttribute("disabled") ||
    element.matches(":disabled") ||
    element.getAttribute("tabindex") === "-1" ||
    hasHiddenOrInertAncestor(element) ||
    isConcealedByClosedDetails(element)
  ) {
    return false;
  }

  return element.getClientRects().length > 0;
}

function hasHiddenOrInertAncestor(element: HTMLElement): boolean {
  let current: HTMLElement | null = element;
  while (current) {
    if (
      current.hasAttribute("hidden") ||
      current.hasAttribute("inert") ||
      current.getAttribute("aria-hidden") === "true"
    ) {
      return true;
    }
    current = current.parentElement;
  }
  return false;
}

function isConcealedByClosedDetails(element: HTMLElement): boolean {
  let current = element.parentElement;
  while (current) {
    if (current.tagName === "DETAILS" && !current.hasAttribute("open")) {
      const summary = Array.from(current.children).find(
        (child) => child.tagName === "SUMMARY",
      );
      if (summary !== element) {
        return true;
      }
    }
    current = current.parentElement;
  }
  return false;
}

export function shouldCloseTopModal(key: string, isTopLayer: boolean): boolean {
  return key === "Escape" && isTopLayer;
}

type ModalBackgroundTarget = Pick<
  HTMLElement,
  "getAttribute" | "hasAttribute" | "setAttribute" | "removeAttribute"
>;

export type ModalBackgroundSnapshot = {
  ariaHidden: string | null;
  inert: boolean;
};

export type ModalBackgroundRecord = {
  target: ModalBackgroundTarget;
  snapshot: ModalBackgroundSnapshot;
};

export function uniqueModalBackgroundTargets(
  explicit: ModalBackgroundTarget | null,
  documentSiblings: ModalBackgroundTarget[],
): ModalBackgroundTarget[] {
  return Array.from(new Set([
    ...(explicit ? [explicit] : []),
    ...documentSiblings,
  ]));
}

export function isolateModalBackgrounds(
  backgrounds: ModalBackgroundTarget[],
): ModalBackgroundRecord[] {
  return backgrounds.flatMap((target) => {
    const snapshot = isolateModalBackground(target);
    return snapshot ? [{ target, snapshot }] : [];
  });
}

export function restoreModalBackgrounds(records: ModalBackgroundRecord[]): void {
  records.slice().reverse().forEach(({ target, snapshot }) => {
    restoreModalBackground(target, snapshot);
  });
}

export function isolateModalBackground(
  background: ModalBackgroundTarget | null,
): ModalBackgroundSnapshot | null {
  if (!background) {
    return null;
  }

  const snapshot = {
    ariaHidden: background.getAttribute("aria-hidden"),
    inert: background.hasAttribute("inert"),
  };
  background.setAttribute("aria-hidden", "true");
  background.setAttribute("inert", "");
  return snapshot;
}

export function restoreModalBackground(
  background: ModalBackgroundTarget | null,
  snapshot: ModalBackgroundSnapshot | null,
): void {
  if (!background || !snapshot) {
    return;
  }

  if (snapshot.ariaHidden === null) {
    background.removeAttribute("aria-hidden");
  } else {
    background.setAttribute("aria-hidden", snapshot.ariaHidden);
  }
  if (!snapshot.inert) {
    background.removeAttribute("inert");
  }
}

export function restoreModalOpener(
  opener: Pick<HTMLElement, "isConnected" | "focus"> | null,
): boolean {
  if (!opener?.isConnected) {
    return false;
  }
  opener.focus();
  return true;
}
