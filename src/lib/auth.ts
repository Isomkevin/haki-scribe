import { useSyncExternalStore } from "react";
import type { AuthUser } from "./hakiscribe";

const STORAGE_KEY = "hakiscribe.session";

export interface StoredSession {
  token: string;
  user: AuthUser;
}

let cached: StoredSession | null | undefined;
const listeners = new Set<() => void>();

function read(): StoredSession | null {
  if (typeof window === "undefined") return null;
  if (cached !== undefined) return cached;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    cached = raw ? (JSON.parse(raw) as StoredSession) : null;
  } catch {
    cached = null;
  }
  return cached;
}

function emit() {
  for (const listener of listeners) listener();
}

export function signIn(session: StoredSession) {
  cached = session;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    /* private mode — the session simply lasts for this tab */
  }
  emit();
}

export function signOut() {
  cached = null;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* nothing to clear */
  }
  emit();
}

export function currentSession(): StoredSession | null {
  return read();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  const onStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY) {
      cached = undefined;
      listener();
    }
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

/** Null while the page is still rendering on the server or hydrating. */
export function useAuth(): { session: StoredSession | null; ready: boolean } {
  const session = useSyncExternalStore(
    subscribe,
    () => read(),
    () => null,
  );
  const ready = typeof window !== "undefined";
  return { session, ready };
}
