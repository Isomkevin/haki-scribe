import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import {
  isDemoDataEnabled,
  loadWorkspaceSettings,
  saveWorkspaceSettings,
  setDemoDataEnabled,
} from "@/lib/workspace-settings";

export const DEMO_MODE_EVENT = "hakiscribe:demo-mode";

type DemoModeListener = () => void;

const listeners = new Set<DemoModeListener>();

function subscribe(listener: DemoModeListener) {
  listeners.add(listener);
  if (typeof window !== "undefined") {
    window.addEventListener(DEMO_MODE_EVENT, listener);
    window.addEventListener("storage", listener);
  }
  return () => {
    listeners.delete(listener);
    if (typeof window !== "undefined") {
      window.removeEventListener(DEMO_MODE_EVENT, listener);
      window.removeEventListener("storage", listener);
    }
  };
}

function getSnapshot() {
  return isDemoDataEnabled();
}

function getServerSnapshot() {
  return true;
}

function notifyDemoModeListeners() {
  for (const listener of listeners) listener();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(DEMO_MODE_EVENT));
  }
}

/** Synchronous preference for first paint — no flash of the wrong mode. */
export function readDemoDataEnabled(): boolean {
  return isDemoDataEnabled();
}

/**
 * Single source of truth for whether seeded demo desk data should appear.
 * Does not control the login demo-credentials CTA.
 */
export function useDemoMode() {
  const enabled = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const setEnabled = useCallback((next: boolean) => {
    setDemoDataEnabled(next);
    notifyDemoModeListeners();
  }, []);

  const toggle = useCallback(() => {
    setEnabled(!isDemoDataEnabled());
  }, [setEnabled]);

  return { enabled, setEnabled, toggle };
}

/** Ensure settings object stays in sync if another tab flips the flag. */
export function useWorkspaceSettingsLive() {
  const [settings, setSettings] = useState(() => loadWorkspaceSettings());
  useEffect(() => {
    return subscribe(() => setSettings(loadWorkspaceSettings()));
  }, []);
  return {
    settings,
    save: (next: typeof settings) => {
      saveWorkspaceSettings(next);
      notifyDemoModeListeners();
      setSettings(next);
    },
  };
}
