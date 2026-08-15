"use client";

import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";
import {
  focusLoopDecision,
  isolateModalBackgrounds,
  MODAL_FOCUSABLE_SELECTOR,
  modalTabStops,
  restoreModalBackgrounds,
  restoreModalOpener,
  shouldCloseTopModal,
  uniqueModalBackgroundTargets,
} from "./accessible-modal-contract";

const modalStack: symbol[] = [];

export function AccessibleModal({
  backgroundRef,
  opener,
  onClose,
  layerClassName,
  backdropClassName,
  dialogClassName,
  label,
  labelledBy,
  focusReturnTiming = "after-paint",
  children,
}: {
  backgroundRef: RefObject<HTMLElement | null>;
  opener: HTMLElement | null;
  onClose: () => void;
  layerClassName: string;
  backdropClassName: string;
  dialogClassName: string;
  label?: string;
  labelledBy?: string;
  focusReturnTiming?: "after-paint" | "synchronous";
  children: ReactNode;
}) {
  const dialogRef = useRef<HTMLElement>(null);
  const layerRef = useRef<HTMLDivElement>(null);
  const tokenRef = useRef(Symbol("watchsignal-modal"));
  const onCloseRef = useRef(onClose);
  const [portalReady, setPortalReady] = useState(false);
  onCloseRef.current = onClose;

  useEffect(() => {
    setPortalReady(true);
  }, []);

  useEffect(() => {
    if (!portalReady || !layerRef.current) {
      return;
    }

    const token = tokenRef.current;
    const background = backgroundRef.current;
    const layer = layerRef.current;
    const documentSiblings = Array.from(document.body.children).filter(
      (element): element is HTMLElement =>
        element !== layer && element instanceof HTMLElement,
    );

    modalStack.push(token);
    const backgroundRecords = isolateModalBackgrounds(
      uniqueModalBackgroundTargets(background, documentSiblings),
    );

    const focusTarget = focusableElements(dialogRef.current)[0] ?? dialogRef.current;
    focusTarget?.focus();

    function handleDocumentKeyDown(event: KeyboardEvent) {
      if (!shouldCloseTopModal(event.key, isTopModal(token))) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      onCloseRef.current();
    }

    document.addEventListener("keydown", handleDocumentKeyDown, true);

    return () => {
      document.removeEventListener("keydown", handleDocumentKeyDown, true);
      const stackIndex = modalStack.lastIndexOf(token);
      if (stackIndex >= 0) {
        modalStack.splice(stackIndex, 1);
      }

      restoreModalBackgrounds(backgroundRecords);

      if (focusReturnTiming === "synchronous") {
        restoreModalOpener(opener);
      } else {
        window.requestAnimationFrame(() => {
          restoreModalOpener(opener);
        });
      }
    };
  }, [backgroundRef, focusReturnTiming, opener, portalReady]);

  function trapFocus(event: ReactKeyboardEvent<HTMLElement>) {
    if (event.key !== "Tab" || !isTopModal(tokenRef.current)) {
      return;
    }

    const focusable = focusableElements(dialogRef.current);
    const activeIndex = focusable.indexOf(document.activeElement as HTMLElement);
    const decision = focusLoopDecision({
      focusableCount: focusable.length,
      activeIndex,
      shiftKey: event.shiftKey,
    });

    if (decision === "native") {
      return;
    }

    event.preventDefault();
    if (decision === "container") {
      dialogRef.current?.focus();
    } else if (decision === "first") {
      focusable[0]?.focus();
    } else {
      focusable.at(-1)?.focus();
    }
  }

  if (!portalReady) {
    return null;
  }

  return createPortal(
    <div ref={layerRef} className={layerClassName} data-watchsignal-modal-layer>
      <div
        className={backdropClassName}
        role="presentation"
        onMouseDown={(event) => {
          if (event.target === event.currentTarget && isTopModal(tokenRef.current)) {
            onCloseRef.current();
          }
        }}
      />
      <section
        ref={dialogRef}
        className={dialogClassName}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        aria-labelledby={labelledBy}
        tabIndex={-1}
        onKeyDown={trapFocus}
      >
        {children}
      </section>
    </div>,
    document.body,
  );
}

function isTopModal(token: symbol): boolean {
  return modalStack.at(-1) === token;
}

function focusableElements(container: HTMLElement | null): HTMLElement[] {
  if (!container) {
    return [];
  }

  return modalTabStops(
    Array.from(
      container.querySelectorAll<HTMLElement>(MODAL_FOCUSABLE_SELECTOR),
    ),
  );
}
