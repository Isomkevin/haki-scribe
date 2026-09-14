export type SessionSource = "mic" | "omi";
export type SessionStatus = "recording" | "processing" | "ready" | "exported";
export type ActionType =
  | "draft_document"
  | "calendar_event"
  | "workspace_matter"
  | "crm_entry"
  | "private_note"
  | "time_entry"
  | "legal_research"
  | "web_search"
  | "llm_task";

export interface ResearchSource {
  title: string | null;
  url: string | null;
  published: string | null;
  extract: string | null;
  citation?: string | null;
  kind?: string | null;
}

export interface NewsHit {
  id?: string;
  title: string | null;
  url: string | null;
  published: string | null;
  extract: string | null;
  topic?: string;
  received_at?: string;
  citation?: string | null;
  kind?: string | null;
  connection?: string[];
  relevance?: number;
  session_id?: string | null;
  matter_id?: string | null;
  matter_name?: string | null;
}

export interface LegalIntelScope {
  session_id?: string | null;
  matter_id?: string | null;
  matter_name?: string | null;
  client_name?: string | null;
  session_title?: string | null;
  has_transcript?: boolean;
  terms?: string[];
}

export interface LegalIntelResult {
  grounded: boolean;
  query?: string | null;
  scope?: LegalIntelScope | null;
  hits: NewsHit[];
  dropped?: number;
  configured: boolean;
  reason?: string | null;
  monitor?: { id?: string; topic?: string; status?: string } | null;
  created?: boolean;
}

export interface ModelOption {
  id: string;
  label: string;
}

export interface ModelCatalogue {
  configured: boolean;
  default: string;
  models: ModelOption[];
}

export interface Matter {
  id: string;
  client_name: string;
  matter_name: string;
  session_ids?: string[];
  contact_ids?: string[];
  created_at: string;
}

export interface Contact {
  id: string;
  name: string;
  updates: Record<string, unknown>;
  matter_id: string | null;
  session_id: string | null;
  created_at: string;
}

export interface Session {
  id: string;
  title: string;
  source: SessionSource;
  language_hint: string | null;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  matters?: Matter[];
  contacts?: Contact[];
  generated_types?: ActionType[];
}

export interface TranscriptSegment {
  id: string;
  session_id: string;
  speaker: string | null;
  text: string;
  start_ms: number;
  end_ms: number;
  confidence: number | null;
  redacted: boolean;
}

export interface FlaggedMoment {
  id: string;
  session_id: string;
  at_ms: number;
  label: string | null;
}

export interface DetectedAction {
  id: string;
  session_id: string;
  type: ActionType;
  title: string;
  preview: string;
  confidence: number;
  confidence_reason: string | null;
  source_segment_id: string | null;
  extracted_fields: Record<string, unknown>;
  pre_checked: boolean;
  status: "detected" | "generated" | "dismissed" | "error";
}

export interface ActionResult {
  action_id: string;
  type: ActionType;
  status: "success" | "error";
  result: Record<string, unknown>;
  error: string | null;
  created_at?: string | null;
}

export interface SessionDetail extends Session {
  transcript: TranscriptSegment[];
  detected_actions: DetectedAction[];
  flagged_moments: FlaggedMoment[];
  action_results?: ActionResult[];
}

export interface IntegrationField {
  id: string;
  label: string;
  type: "password" | "text";
  help: string;
  placeholder: string;
  mask: boolean;
}

export interface Integration {
  provider_id: string;
  name: string;
  group: "ai" | "storage" | "practice";
  what_it_does: string;
  capabilities: string[];
  fields: IntegrationField[];
  connected: boolean;
  connected_at: string | null;
  masked_creds: Record<string, string>;
}

export interface IntegrationStatus {
  provider_id: string;
  name: string;
  connected: boolean;
  connected_at: string;
  masked_creds: Record<string, string>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
  }
}

const PRODUCTION_API_URL = "https://hakiscribe-backend.onrender.com";

const configuredBaseUrl = (
  (import.meta.env["VITE_API_BASE_URL"] as string | undefined)?.trim() ||
  (import.meta.env.PROD ? PRODUCTION_API_URL : "")
).replace(/\/$/, "");

export const hasApiConfiguration = Boolean(configuredBaseUrl);
export const apiBaseUrl = configuredBaseUrl;

export interface HealthStatus {
  status: string;
  integrations?: Record<string, boolean>;
  environments?: string[];
  webhook?: string;
}

function apiUrl(path: string) {
  if (!configuredBaseUrl) {
    throw new ApiError("HakiScribe cannot reach its service because VITE_API_BASE_URL is not configured.");
  }
  return `${configuredBaseUrl}${path}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      ...init,
      headers: {
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError("We couldn’t connect to the HakiScribe service. Check the service URL and try again.");
  }
  if (!response.ok) {
    const body = await response.text();
    let message = body || `Request failed (${response.status})`;
    try {
      const parsed = JSON.parse(body) as { detail?: string; message?: string };
      message = parsed.detail ?? parsed.message ?? message;
    } catch {
      // Keep the server's plain-text response.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export const hakiApi = {
  listSessions: () => request<Session[]>("/sessions"),
  getSession: (id: string) => request<SessionDetail>(`/sessions/${id}`),
  createSession: (body: { title: string; source: SessionSource; language_hint?: string }) =>
    request<Session>("/sessions", { method: "POST", body: JSON.stringify(body) }),
  flagMoment: (id: string, body: { at_ms: number; label?: string }) =>
    request<FlaggedMoment>(`/sessions/${id}/flags`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateSpeakers: (id: string, mapping: Record<string, string>) =>
    request<TranscriptSegment[]>(`/sessions/${id}/speakers`, {
      method: "POST",
      body: JSON.stringify({ mapping }),
    }),
  redactSegment: (sessionId: string, segmentId: string, redacted: boolean) =>
    request<TranscriptSegment>(`/sessions/${sessionId}/segments/${segmentId}`, {
      method: "PATCH",
      body: JSON.stringify({ redacted }),
    }),
  updateSegmentText: (sessionId: string, segmentId: string, text: string) =>
    request<TranscriptSegment>(`/sessions/${sessionId}/segments/${segmentId}`, {
      method: "PATCH",
      body: JSON.stringify({ text }),
    }),
  finalize: (id: string) => request<Session>(`/sessions/${id}/finalize`, { method: "POST" }),
  detect: (id: string, force = false) =>
    request<DetectedAction[]>(`/sessions/${id}/detect${force ? "?force=true" : ""}`, { method: "POST" }),
  dismissAction: (sessionId: string, actionId: string) =>
    request<DetectedAction>(`/sessions/${sessionId}/actions/${actionId}/dismiss`, { method: "POST" }),
  listActions: (id: string) => request<DetectedAction[]>(`/sessions/${id}/actions`),
  generate: (id: string, actionIds: string[], fieldOverrides?: Record<string, Record<string, unknown>>) =>
    request<ActionResult[]>(`/sessions/${id}/generate`, {
      method: "POST",
      body: JSON.stringify({ action_ids: actionIds, field_overrides: fieldOverrides ?? {} }),
    }),
  ask: (id: string, body: { instruction: string; model?: string }) =>
    request<ActionResult>(`/sessions/${id}/ask`, { method: "POST", body: JSON.stringify(body) }),
  listModels: () => request<ModelCatalogue>("/models"),
  listMatters: () => request<Matter[]>("/matters"),
  createMatter: (body: { client_name: string; matter_name: string; session_id?: string }) =>
    request<Matter>("/matters", { method: "POST", body: JSON.stringify(body) }),
  listContacts: () => request<Contact[]>("/contacts"),
  createContact: (body: { name: string; updates?: Record<string, unknown>; matter_id?: string; session_id?: string }) =>
    request<Contact>("/contacts", { method: "POST", body: JSON.stringify(body) }),
  health: () => request<HealthStatus>("/health"),
  listIntegrations: () => request<Integration[]>("/integrations"),
  connectIntegration: (providerId: string, credentials: Record<string, string>) =>
    request<IntegrationStatus>(`/integrations/${providerId}`, {
      method: "POST",
      body: JSON.stringify({ credentials }),
    }),
  disconnectIntegration: (providerId: string) =>
    request<{ provider_id: string; connected: boolean }>(`/integrations/${providerId}`, {
      method: "DELETE",
    }),
  exportDocument: (sessionId: string, actionId: string, provider: string) =>
    request<{ ok: boolean; url: string | null; provider: string }>(
      `/integrations/${sessionId}/documents/${actionId}/export`,
      { method: "POST", body: JSON.stringify({ provider }) },
    ),
  ensureShowcase: () => request<SessionDetail>("/demo/showcase", { method: "POST" }),
  syncDemoLibrary: () =>
    request<{ created: number; reused: number; completing: boolean; sessions: Session[] }>("/demo/sync", {
      method: "POST",
    }),
  searchLegalIntel: (body: { session_id?: string | undefined; matter_id?: string | undefined; query?: string }) =>
    request<LegalIntelResult>("/news/search", { method: "POST", body: JSON.stringify(body) }),
  watchLegalIntel: (body: { session_id?: string | undefined; matter_id?: string | undefined }) =>
    request<LegalIntelResult>("/news/watch", { method: "POST", body: JSON.stringify(body) }),
  listLegalIntel: (params?: { session_id?: string | undefined; matter_id?: string | undefined }) => {
    const query = new URLSearchParams();
    if (params?.session_id) query.set("session_id", params.session_id);
    if (params?.matter_id) query.set("matter_id", params.matter_id);
    const suffix = query.toString();
    return request<{ hits: NewsHit[]; monitors: { topic: string; status?: string }[] }>(
      `/news/hits${suffix ? `?${suffix}` : ""}`,
    );
  },
};

export function omiWebhookUrl(sessionId: string) {
  return `${configuredBaseUrl}/webhooks/omi?session_id=${sessionId}`;
}

export function whatsappShareUrl(text: string) {
  return `https://wa.me/?text=${encodeURIComponent(text.slice(0, 1800))}`;
}

export function downloadTextFile(filename: string, contents: string) {
  const blob = new Blob([contents], { type: "text/plain;charset=utf-8" });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(href);
}

export function websocketUrl(sessionId: string) {
  const url = new URL(apiUrl(`/sessions/${sessionId}/stream`));
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export function formatDuration(milliseconds: number) {
  const seconds = Math.floor(milliseconds / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

export function displayValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(displayValue).join(", ");
  if (value && typeof value === "object") return JSON.stringify(value, null, 2);
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}