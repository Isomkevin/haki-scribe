import type { SessionSource } from "@/lib/hakiscribe";

export const SETTINGS_SECTIONS = ["profile", "workspace", "security", "connectors", "about"] as const;
export type SettingsSection = (typeof SETTINGS_SECTIONS)[number];

export const PRACTICE_ROLES = [
  { id: "advocate", label: "Advocate" },
  { id: "pupil", label: "Pupil" },
  { id: "clerk", label: "Legal clerk" },
  { id: "manager", label: "Practice manager" },
  { id: "other", label: "Other" },
] as const;

export const LANGUAGE_OPTIONS = [
  { id: "code-switch", label: "English + Kiswahili" },
  { id: "multilingual", label: "Multilingual / African code-switch (Sahara)" },
  { id: "en", label: "English" },
  { id: "sw", label: "Kiswahili" },
] as const;

export function usesSaharaRefine(languageHint: string | null | undefined): boolean {
  return languageHint === "code-switch" || languageHint === "multilingual";
}

/** Explicit opt-in or auto-detected code-switch / multilingual captions. */
export function shouldAutoSaharaRefine(
  languageHint: string | null | undefined,
  detectedMode: string | null | undefined,
): boolean {
  return usesSaharaRefine(languageHint) || detectedMode === "code-switch" || detectedMode === "multilingual";
}

export interface WorkspaceProfile {
  displayName: string;
  practiceName: string;
  email: string;
  role: string;
}

export interface WorkspaceDefaults {
  defaultLanguage: string;
  defaultSource: SessionSource;
}

export interface WorkspaceSettings {
  profile: WorkspaceProfile;
  workspace: WorkspaceDefaults;
}

const STORAGE_KEY = "hakiscribe.workspace-settings";

export const defaultWorkspaceSettings = (): WorkspaceSettings => ({
  profile: {
    displayName: "",
    practiceName: "",
    email: "",
    role: "advocate",
  },
  workspace: {
    defaultLanguage: "code-switch",
    defaultSource: "mic",
  },
});

function isSessionSource(value: unknown): value is SessionSource {
  return value === "mic" || value === "omi";
}

export function loadWorkspaceSettings(): WorkspaceSettings {
  const defaults = defaultWorkspaceSettings();
  if (typeof window === "undefined") return defaults;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw) as Partial<WorkspaceSettings>;
    return {
      profile: {
        displayName: String(parsed.profile?.displayName ?? defaults.profile.displayName),
        practiceName: String(parsed.profile?.practiceName ?? defaults.profile.practiceName),
        email: String(parsed.profile?.email ?? defaults.profile.email),
        role: String(parsed.profile?.role ?? defaults.profile.role),
      },
      workspace: {
        defaultLanguage: String(parsed.workspace?.defaultLanguage ?? defaults.workspace.defaultLanguage),
        defaultSource: isSessionSource(parsed.workspace?.defaultSource)
          ? parsed.workspace.defaultSource
          : defaults.workspace.defaultSource,
      },
    };
  } catch {
    return defaults;
  }
}

export function saveWorkspaceSettings(settings: WorkspaceSettings) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}
