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

/** Session language modes — pairs map to Sahara ASR codes on refine. */
export const LANGUAGE_OPTIONS = [
  { id: "code-switch", label: "English + Kiswahili", group: "pairs" },
  { id: "en-ha", label: "English + Hausa", group: "pairs" },
  { id: "en-yo", label: "English + Yoruba", group: "pairs" },
  { id: "en-ig", label: "English + Igbo", group: "pairs" },
  { id: "en-zu", label: "English + Zulu", group: "pairs" },
  { id: "en-xh", label: "English + Xhosa", group: "pairs" },
  { id: "en-rw", label: "English + Kinyarwanda", group: "pairs" },
  { id: "en-lg", label: "English + Luganda", group: "pairs" },
  { id: "en-pcm", label: "English + Nigerian Pidgin", group: "pairs" },
  { id: "fr-rw", label: "French + Kinyarwanda", group: "pairs" },
  { id: "multilingual", label: "Multilingual / African code-switch", group: "pairs" },
  { id: "en", label: "English", group: "mono" },
  { id: "sw", label: "Kiswahili", group: "mono" },
  { id: "ha", label: "Hausa", group: "mono" },
  { id: "yo", label: "Yoruba", group: "mono" },
  { id: "ig", label: "Igbo", group: "mono" },
  { id: "zu", label: "Zulu", group: "mono" },
  { id: "xh", label: "Xhosa", group: "mono" },
  { id: "rw", label: "Kinyarwanda", group: "mono" },
  { id: "lg", label: "Luganda", group: "mono" },
  { id: "pcm", label: "Nigerian Pidgin", group: "mono" },
  { id: "fr", label: "French", group: "mono" },
] as const;

const PAIR_OR_MULTI = new Set<string>(
  LANGUAGE_OPTIONS.filter((o) => o.group === "pairs").map((o) => o.id),
);
const AFRICAN_MONO = new Set<string>(
  LANGUAGE_OPTIONS.filter((o) => o.group === "mono" && o.id !== "en").map((o) => o.id),
);

export function languageLabel(languageHint: string | null | undefined): string {
  if (!languageHint) return "";
  const hit = LANGUAGE_OPTIONS.find((o) => o.id === languageHint);
  return hit?.label ?? languageHint;
}

export function usesSaharaRefine(languageHint: string | null | undefined): boolean {
  if (!languageHint) return false;
  return PAIR_OR_MULTI.has(languageHint as (typeof LANGUAGE_OPTIONS)[number]["id"]) || AFRICAN_MONO.has(languageHint as (typeof LANGUAGE_OPTIONS)[number]["id"]);
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
  useDemoData: boolean;
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
