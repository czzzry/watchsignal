"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import {
  createStandaloneBackHandlerRegistry,
  createStandaloneBackNavigationController,
  standaloneUnhandledBackAction,
} from "./standalone-back-navigation-contract";

type RegisterBackHandler = (
  handler: () => void,
  priority: number,
) => () => void;

const StandaloneBackNavigationContext = createContext<RegisterBackHandler | null>(null);

export function StandaloneBackNavigationProvider({
  children,
}: {
  children: ReactNode;
}) {
  const registry = useMemo(() => createStandaloneBackHandlerRegistry(), []);
  const register = useCallback<RegisterBackHandler>(
    (handler, priority) => registry.register(handler, priority),
    [registry],
  );

  useEffect(() => {
    const navigatorWithStandalone = navigator as Navigator & {
      standalone?: boolean;
    };
    const standalone = window.matchMedia("(display-mode: standalone)").matches ||
      navigatorWithStandalone.standalone === true;
    const controller = createStandaloneBackNavigationController({
      standalone,
      history: window.history,
      listen(listener) {
        window.addEventListener("popstate", listener);
        return () => window.removeEventListener("popstate", listener);
      },
      onBack() {
        if (registry.handleBack()) return;
        if (standaloneUnhandledBackAction(window.location.pathname) === "home") {
          window.location.assign("/");
        }
      },
    });

    controller.start();
    return controller.stop;
  }, [registry]);

  return (
    <StandaloneBackNavigationContext.Provider value={register}>
      {children}
    </StandaloneBackNavigationContext.Provider>
  );
}

export function useStandaloneBackHandler({
  active,
  onBack,
  priority = 0,
}: {
  active: boolean;
  onBack: () => void;
  priority?: number;
}) {
  const register = useContext(StandaloneBackNavigationContext);
  const handlerRef = useRef(onBack);
  handlerRef.current = onBack;

  useEffect(() => {
    if (!active || !register) return;
    return register(() => handlerRef.current(), priority);
  }, [active, priority, register]);
}
