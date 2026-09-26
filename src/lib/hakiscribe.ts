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
  session_ids?: string[];
  ambiguous_contact_id?: string | null;
  created_at: string;
}

export interface ContactUpdate {
  name?: string;
  updates?: Record<string, unknown>;
  matter_id?: string;
  clear_matter?: boolean;
  session_ids?: string[];
}

export interface Session {
  id: string;
  title: string;
  source: SessionSource;
  language_hint: string | null;
  detected_language?: string | null;
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

export interface IntegrationOAuthSetup {
  console: string;
  redirect_uri: string;
  client_id_env: string;
  client_secret_env: string;
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
  source?: "workspace" | "user" | null;
  account?: string | null;
  auth?: "oauth" | "api_key";
  oauth?: boolean;
  oauth_configured?: boolean;
  oauth_setup?: IntegrationOAuthSetup | null;
  masked_creds: Record<string, string>;
  health?: ConnectorHealthState;
  health_error?: string | null;
  last_checked_at?: string | null;
}

export type ConnectorHealthState = "valid" | "expired" | "invalid" | "unreachable" | "not_connected" | "unchecked";

export interface ConnectorHealth {
  provider_id: string;
  health: ConnectorHealthState;
  health_error: string | null;
  last_checked_at: string | null;
}

export function reauthProvider(error: unknown): string | null {
  return (error as { reauthProvider?: string } | null)?.reauthProvider || null;
}

export interface OAuthOutcome {
  outcome: "connected" | "failed" | "closed";
  reason?: string | undefined;
  message?: string | undefined;
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
  omi_miniapp?: {
    webhook_url: string;
    auth_url: string;
    setup_completed_url: string;
    linked: boolean;
  };
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  model?: string | null;
  error?: boolean;
  created_at: string;
}

export interface ChatThread {
  id: string;
  session_id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface OmiStatus {
  linked: boolean;
  connected?: boolean;
  app_linked?: boolean;
  api_key_connected?: boolean;
  uid: string | null;
  masked_uid: string | null;
  connected_at: string | null;
  last_activity_at?: string | null;
  active_session_id?: string | null;
  webhook_url: string;
  auth_url: string;
  setup_completed_url: string;
}

const GENERIC_HTTP_MESSAGES = new Set([
  "not found",
  "internal server error",
  "bad request",
  "unauthorized",
  "forbidden",
  "method not allowed",
  "bad gateway",
  "service unavailable",
  "gateway timeout",
  "error",
  "ok",
]);

function extractErrorDetail(body: string): string {
  if (!body.trim()) return "";
  try {
    const parsed = JSON.parse(body) as {
      detail?: string | Array<{ msg?: string; message?: string }> | Record<string, unknown>;
      message?: string;
      error?: string;
    };
    if (typeof parsed.detail === "string" && parsed.detail.trim()) return parsed.detail.trim();
    if (parsed.detail && !Array.isArray(parsed.detail) && typeof parsed.detail === "object") {
      const d = parsed.detail as { code?: string; provider?: string; message?: string };
      if (d.code === "reauth_required") return `__reauth__:${d.provider ?? ""}:${d.message ?? ""}`;
      if (typeof d.message === "string") return d.message;
    }
    if (Array.isArray(parsed.detail)) {
      const parts = parsed.detail
        .map((item) => (typeof item === "string" ? item : item.msg ?? item.message ?? ""))
        .map((part) => part.trim())
        .filter(Boolean);
      if (parts.length) return parts.join(" ");
    }
    if (typeof parsed.message === "string" && parsed.message.trim()) return parsed.message.trim();
    if (typeof parsed.error === "string" && parsed.error.trim()) return parsed.error.trim();
  } catch {
    // Plain-text or HTML body from a proxy / older server.
  }
  const plain = body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  if (plain.length > 180) return "";
  return plain;
}

function isGenericHttpMessage(message: string) {
  const normalized = message.trim().toLowerCase().replace(/[.!]+$/, "");
  return !normalized || GENERIC_HTTP_MESSAGES.has(normalized) || /^\d{3}\s/.test(normalized);
}

function humanizeApiFailure(status: number, rawMessage: string, path: string): string {
  const message = rawMessage.trim();
  if (message && !isGenericHttpMessage(message)) return message;

  const normalized = message.toLowerCase().replace(/[.!]+$/, "");
  const effectiveStatus =
    status ||
    (normalized === "not found"
      ? 404
      : normalized === "bad request"
        ? 400
        : normalized === "unauthorized"
          ? 401
          : normalized === "forbidden"
            ? 403
            : normalized === "method not allowed"
              ? 405
              : normalized.includes("timeout") || normalized === "gateway timeout"
                ? 504
                : normalized === "service unavailable" || normalized === "bad gateway" || normalized === "internal server error"
                  ? 500
                  : 0);

  if (effectiveStatus === 404) {
    if (path.startsWith("/integrations")) {
      return "Connectors are unavailable on this service. Confirm the HakiScribe backend is running and up to date, then try again.";
    }
    if (path.startsWith("/sessions")) {
      return "That session could not be found. It may have been removed, or the service URL is pointing at the wrong environment.";
    }
    if (path.startsWith("/health")) {
      return "The workspace health check is missing on this service. Confirm the backend is running the latest HakiScribe build.";
    }
    return "We could not find what you asked for. Refresh the page or check that the service is running the latest build.";
  }
  if (effectiveStatus === 400) {
    return "The request could not be completed. Check the details you entered and try again.";
  }
  if (effectiveStatus === 401 || effectiveStatus === 403) {
    return "This workspace is not authorised for that action. Check your service credentials and try again.";
  }
  if (effectiveStatus === 408 || effectiveStatus === 504) {
    return "The service took too long to respond. Try again in a moment.";
  }
  if (effectiveStatus === 429) {
    return "Too many requests were sent just now. Wait a moment, then try again.";
  }
  if (effectiveStatus >= 500) {
    return "The HakiScribe service hit an unexpected problem. Try again in a moment. If it continues, check that the backend is healthy.";
  }
  return "Something went wrong talking to the HakiScribe service. Try again.";
}

/** Prefer this in UI so bare HTTP phrases like "Not Found" never reach the user. */
export function friendlyErrorMessage(error: unknown, fallback = "Something went wrong. Try again.") {
  if (typeof error === "string") {
    if (error && !isGenericHttpMessage(error)) return error;
    return humanizeApiFailure(0, error, "") || fallback;
  }
  if (error instanceof ApiError) {
    if (error.message && !isGenericHttpMessage(error.message)) return error.message;
    return humanizeApiFailure(error.status ?? 0, error.message, "") || fallback;
  }
  if (error instanceof Error) {
    if (error.message && !isGenericHttpMessage(error.message)) return error.message;
    return fallback;
  }
  return fallback;
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
    const detail = extractErrorDetail(body);
    if (detail.startsWith("__reauth__:")) {
      const [, provider = "", ...rest] = detail.split(":");
      const err = new ApiError(rest.join(":") || "Sign in again to continue.", response.status);
      (err as ApiError & { reauthProvider?: string }).reauthProvider = provider;
      throw err;
    }
    throw new ApiError(humanizeApiFailure(response.status, detail, path), response.status);
  }
  return (await response.json()) as T;
}

export interface AuthUser {
  email: string;
  name: string;
  demo?: boolean;
}

export interface DemoCredentials {
  enabled: boolean;
  email?: string;
  password?: string;
  name?: string;
}

/** Matches backend defaults in auth.py — used so the login demo CTA is never blank during cold starts. */
export const FALLBACK_DEMO_CREDENTIALS: DemoCredentials = {
  enabled: true,
  email: "demo@hakiscribe.app",
  password: "hakiscribe-demo",
  name: "Demo Advocate",
};

export const DEMO_CREDENTIALS_QUERY_KEY = ["demo-credentials"] as const;

export const hakiApi = {
  login: (body: { email: string; password: string }) =>
    request<{ token: string; user: AuthUser }>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  demoCredentials: () => request<DemoCredentials>("/auth/demo"),
  listSessions: (opts?: { includeDemo?: boolean }) => {
    const includeDemo = opts?.includeDemo !== false;
    const query = includeDemo ? "" : "?include_demo=false";
    return request<Session[]>(`/sessions${query}`);
  },
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
  finalizeAsr: async (id: string, audio: Blob, filename = "recording.webm", detectedMode?: string | null) => {
    const form = new FormData();
    form.append("audio", audio, filename);
    if (detectedMode) form.append("detected_mode", detectedMode);
    let response: Response;
    try {
      response = await fetch(apiUrl(`/sessions/${id}/asr/finalize`), {
        method: "POST",
        body: form,
      });
    } catch {
      throw new ApiError("We couldn’t connect to the HakiScribe service. Check the service URL and try again.");
    }
    if (!response.ok) {
      const body = await response.text();
      const detail = extractErrorDetail(body);
      throw new ApiError(humanizeApiFailure(response.status, detail, `/sessions/${id}/asr/finalize`), response.status);
    }
    return (await response.json()) as SessionDetail;
  },
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
  getContact: (id: string) => request<Contact>(`/contacts/${id}`),
  updateContact: (id: string, body: ContactUpdate) =>
    request<Contact>(`/contacts/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  health: () => request<HealthStatus>("/health"),
  listIntegrations: () => request<Integration[]>("/integrations"),
  omiStatus: () => request<OmiStatus>("/integrations/omi/status"),
  omiImport: (limit = 10) =>
    request<{ imported: number; skipped: number; session_ids: string[] }>(`/integrations/omi/import?limit=${limit}`, {
      method: "POST",
    }),
  omiSetActive: (sessionId: string) => request<OmiStatus>(`/integrations/omi/active/${sessionId}`, { method: "POST" }),
  listChats: (sessionId: string) => request<ChatThread[]>(`/sessions/${sessionId}/chats`),
  createChat: (sessionId: string, title?: string) =>
    request<ChatThread>(`/sessions/${sessionId}/chats`, { method: "POST", body: JSON.stringify({ title }) }),
  getChat: (sessionId: string, threadId: string) => request<ChatThread>(`/sessions/${sessionId}/chats/${threadId}`),
  deleteChat: (sessionId: string, threadId: string) =>
    request<{ deleted: boolean }>(`/sessions/${sessionId}/chats/${threadId}`, { method: "DELETE" }),
  sendChatMessage: (sessionId: string, threadId: string, body: { content: string; model?: string }) =>
    request<ChatThread>(`/sessions/${sessionId}/chats/${threadId}/messages`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  connectIntegration: (providerId: string, credentials: Record<string, string>) =>
    request<IntegrationStatus>(`/integrations/${providerId}`, {
      method: "POST",
      body: JSON.stringify({ credentials }),
    }),
  checkAllIntegrations: () => request<ConnectorHealth[]>("/integrations/health"),
  checkIntegration: (providerId: string) =>
    request<ConnectorHealth>(`/integrations/${providerId}/check`, { method: "POST" }),
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
  ensureSaharaDemo: () => request<SessionDetail>("/demo/sahara", { method: "POST" }),
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

/** Ping health + demo credentials so a sleeping Render instance starts before sign-in. */
export async function warmWorkspace(): Promise<void> {
  if (!hasApiConfiguration) return;
  await Promise.allSettled([hakiApi.health(), hakiApi.demoCredentials()]);
}

/** URL the connect popup opens; the server bounces it to the provider's consent screen. */
export function integrationOAuthUrl(providerId: string, params?: Record<string, string>) {
  const base = configuredBaseUrl || PRODUCTION_API_URL;
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value) query.set(key, value);
  }
  const suffix = query.toString();
  return `${base}/integrations/oauth/${providerId}/start${suffix ? `?${suffix}` : ""}`;
}

/** Opens the provider consent popup and resolves once it reports back. */
export function startIntegrationOAuth(
  providerId: string,
  params?: Record<string, string>,
): Promise<OAuthOutcome> {
  return new Promise((resolve, reject) => {
    const popup = window.open(integrationOAuthUrl(providerId, params), "hakiscribe-oauth", "width=520,height=680");
    if (!popup) {
      reject(new Error("Your browser blocked the sign-in window. Allow pop-ups for HakiScribe and try again."));
      return;
    }
    let done = false;
    const cleanup = () => {
      window.removeEventListener("message", onMessage);
      window.clearInterval(poll);
    };
    const onMessage = (event: MessageEvent) => {
      const data = event.data as { source?: string; provider?: string; status?: string; reason?: string; message?: string } | null;
      if (!data || data.source !== "hakiscribe-oauth" || data.provider !== providerId) return;
      done = true;
      cleanup();
      popup.close();
      resolve(
        data.status === "connected"
          ? { outcome: "connected" }
          : { outcome: "failed", reason: data.reason, message: data.message },
      );
    };
    window.addEventListener("message", onMessage);
    const poll = window.setInterval(() => {
      if (!popup.closed || done) return;
      cleanup();
      resolve({ outcome: "closed", message: "The sign-in window was closed before it finished. Nothing was changed." });
    }, 600);
  });
}

export function omiWebhookUrl(sessionId: string, webhookBase?: string) {
  const url = new URL(webhookBase ?? `${configuredBaseUrl || PRODUCTION_API_URL}/webhooks/omi`);
  // Preserve the optional server-generated webhook token for legacy pairing.
  url.searchParams.set("session_id", sessionId);
  return url.toString();
}

export function omiMiniappUrls() {
  const base = configuredBaseUrl || PRODUCTION_API_URL;
  return {
    webhookUrl: `${base}/webhooks/omi`,
    authUrl: `${base}/integrations/omi/auth`,
    setupCompletedUrl: `${base}/integrations/omi/setup-completed`,
  };
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

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const LONG_HEX_PATTERN = /^[0-9a-f]{16,}$/i;
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$/;

/** Opaque system IDs — show quietly as references, not as primary content. */
export function looksLikeTechnicalId(value: unknown): boolean {
  if (typeof value !== "string") return false;
  const text = value.trim();
  if (!text || text.includes(" ")) return false;
  if (UUID_PATTERN.test(text)) return true;
  if (LONG_HEX_PATTERN.test(text)) return true;
  // Long opaque tokens (provider ids, deal ids, etc.)
  if (text.length >= 22 && /^[A-Za-z0-9_\-:.]+$/.test(text) && /\d/.test(text) && /[a-z]/i.test(text)) {
    return true;
  }
  return false;
}

/** Large bodies / handoff payloads rendered elsewhere — keep out of meta grids. */
const PAYLOAD_ONLY_FIELD_KEYS = new Set([
  "ics",
  "whatsapp_share_url",
  "whatsapp_share_text",
  "document_text",
  "note_text",
  "narrative",
  "description",
  "activity_description",
  "background_info",
  "detection_mode",
  "exports",
  "answer",
  "output",
  "question",
  "instruction",
]);

const REFERENCE_FIELD_KEYS = new Set([
  "action_id",
  "session_id",
  "source_segment_id",
  "existing_matter_id",
  "matter_id",
  "contact_id",
  "document_id",
  "calendar_id",
  "ambiguous_document_id",
  "ambiguous_event_id",
  "ambiguous_deal_id",
  "ambiguous_contact_id",
  "workspace_url",
  "ambiguous_document_url",
]);

export function isPayloadOnlyFieldKey(key: string): boolean {
  const normalized = key.trim().toLowerCase();
  if (PAYLOAD_ONLY_FIELD_KEYS.has(normalized)) return true;
  if (normalized.includes("whatsapp_share")) return true;
  return false;
}

export function isReferenceFieldKey(key: string): boolean {
  const normalized = key.trim().toLowerCase();
  if (REFERENCE_FIELD_KEYS.has(normalized)) return true;
  if (normalized.endsWith("_id") || normalized.endsWith("_ids")) return true;
  if (normalized.endsWith("_url") && normalized !== "url") return true;
  if (normalized.startsWith("ambiguous_") && normalized.endsWith("_id")) return true;
  return false;
}

/** @deprecated Prefer isReferenceFieldKey / isPayloadOnlyFieldKey */
export function isTechnicalFieldKey(key: string): boolean {
  return isPayloadOnlyFieldKey(key) || isReferenceFieldKey(key);
}

const FIELD_LABELS: Record<string, string> = {
  duration_hours: "Hours",
  matter_name: "Matter",
  client_name: "Client",
  contact_name: "Contact",
  document_kind: "Document type",
  activity_description: "Activity",
  billable: "Billable",
  attendees: "Attendees",
  location: "Location",
  start: "Starts",
  end: "Ends",
  title: "Title",
  note: "Status",
  updates: "Notes",
  question: "Question",
  answer: "Answer",
  instruction: "Instruction",
  output: "Response",
  model: "Prepared with",
  source: "Source",
  workspace_error: "Workspace note",
  matter_id: "Matter reference",
  contact_id: "Contact reference",
  document_id: "Document reference",
  calendar_id: "Calendar reference",
  existing_matter_id: "Linked matter reference",
  ambiguous_document_id: "Ambiguous document reference",
  ambiguous_event_id: "Ambiguous event reference",
  ambiguous_deal_id: "Ambiguous deal reference",
  ambiguous_contact_id: "Ambiguous contact reference",
  workspace_url: "Workspace link",
  ambiguous_document_url: "Ambiguous document link",
  action_id: "Action reference",
  session_id: "Session reference",
  source_segment_id: "Source line reference",
};

export function humanizeFieldLabel(key: string): string {
  const normalized = key.trim().toLowerCase();
  if (FIELD_LABELS[normalized]) return FIELD_LABELS[normalized];
  return key
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
    .trim();
}

/** Shorten opaque IDs for scanning; full value stays available for copy. */
export function formatReferenceId(value: unknown): string {
  if (value === null || value === undefined) return "—";
  const text = String(value).trim();
  if (!text) return "—";
  if (UUID_PATTERN.test(text)) {
    return `${text.slice(0, 8)}…${text.slice(-4)}`;
  }
  if (text.length > 28) {
    return `${text.slice(0, 10)}…${text.slice(-6)}`;
  }
  return text;
}

export function referenceDisplayValue(key: string, value: unknown): string {
  if (typeof value === "string" && (key.endsWith("_url") || value.startsWith("http"))) {
    return sourceHostname(value) ?? formatReferenceId(value);
  }
  if (looksLikeTechnicalId(value) || isReferenceFieldKey(key)) {
    return formatReferenceId(value);
  }
  return displayValue(value);
}

function formatDateTimeForProfessionals(value: string): string | null {
  if (!ISO_DATE_PATTERN.test(value.trim())) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const hasTime = /T|\d{2}:\d{2}/.test(value);
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...(hasTime
      ? { hour: "numeric", minute: "2-digit" }
      : {}),
  }).format(date);
}

function formatHours(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  const text = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  return `${text} ${rounded === 1 ? "hour" : "hours"}`;
}

export function formatBillableHours(value: unknown): string {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric) || numeric < 0) return displayValue(value);
  return formatHours(numeric);
}

export function friendlyModelName(model: string): string {
  const bare = model.includes(":") ? model.split(":").slice(1).join(":") : model;
  return bare
    .replaceAll("-", " ")
    .replaceAll("_", " ")
    .replace(/\bclaude\b/gi, "Claude")
    .replace(/\bgpt\b/gi, "GPT")
    .replace(/\b(\d) (\d)\b/g, "$1.$2")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

/** Soften internal persistence notes for the review desk. */
export function friendlyStatusNote(note: unknown): string | null {
  if (typeof note !== "string" || !note.trim()) return null;
  const text = note.trim().toLowerCase();
  if (text.includes("linked")) return "Linked to an existing matter in your library";
  if (text.includes("new matter") || text.includes("persisted via")) return "Saved to your Session Library";
  if (text.includes("ambiguous")) return "Also mirrored to Ambiguous";
  if (text.includes("created in")) return "Saved to your connected CRM";
  if (text.includes("session library")) return "Saved to your Session Library";
  if (text.includes("/") || text.includes("_id") || UUID_PATTERN.test(note)) {
    return "Saved for this session";
  }
  return note;
}

export function displayValue(value: unknown): string {
  if (Array.isArray(value)) {
    const parts = value
      .map((item) => displayValue(item))
      .filter((item) => item && item !== "—");
    return parts.length ? parts.join(", ") : "—";
  }
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(([key]) => !isPayloadOnlyFieldKey(key))
      .map(([key, entry]) => {
        const shown = isReferenceFieldKey(key) || looksLikeTechnicalId(entry)
          ? referenceDisplayValue(key, entry)
          : displayValue(entry);
        return `${humanizeFieldLabel(key)}: ${shown}`;
      });
    return entries.length ? entries.join(" · ") : "—";
  }
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "—";
    return Number.isInteger(value) ? String(value) : String(Math.round(value * 100) / 100);
  }
  const text = String(value).trim();
  if (!text) return "—";
  if (looksLikeTechnicalId(text)) return formatReferenceId(text);
  const asDate = formatDateTimeForProfessionals(text);
  if (asDate) return asDate;
  return text;
}

/** Primary practice fields for the review desk (names, times, notes — not system refs). */
export function shouldShowResultField(key: string, value: unknown): boolean {
  if (isPayloadOnlyFieldKey(key) || isReferenceFieldKey(key)) return false;
  if (value === null || value === undefined || value === "") return false;
  if (looksLikeTechnicalId(value)) return false;
  if (typeof value === "object" && !Array.isArray(value)) {
    const visible = Object.entries(value as Record<string, unknown>).filter(
      ([entryKey, entryValue]) => shouldShowResultField(entryKey, entryValue),
    );
    return visible.length > 0;
  }
  if (Array.isArray(value) && value.length === 0) return false;
  return true;
}

/** System references (IDs / links) shown in a quieter secondary section. */
export function shouldShowReferenceField(key: string, value: unknown): boolean {
  if (isPayloadOnlyFieldKey(key)) return false;
  if (value === null || value === undefined || value === "") return false;
  if (isReferenceFieldKey(key)) return true;
  return looksLikeTechnicalId(value);
}

export interface BackgroundSource {
  title: string | null;
  url: string | null;
  published: string | null;
  extract: string | null;
  facts: string[];
}

function looksLikeJsonBlob(text: string): boolean {
  const trimmed = text.trim();
  return (
    (trimmed.startsWith("{") && trimmed.includes('"')) ||
    (trimmed.startsWith("[") && trimmed.includes("{"))
  );
}

function tryParseJson(text: string): unknown | null {
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return null;
  try {
    return JSON.parse(trimmed) as unknown;
  } catch {
    // Exa highlights sometimes land with literal newlines inside an otherwise JSON-shaped string.
  }
  try {
    const repaired = trimmed
      .replace(/\r\n/g, "\\n")
      .replace(/\r/g, "\\n")
      .replace(/\n/g, "\\n")
      .replace(/\t/g, "\\t");
    return JSON.parse(repaired) as unknown;
  } catch {
    return null;
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === "object" && !Array.isArray(value)) return value as Record<string, unknown>;
  if (typeof value !== "string") return null;
  const parsed = tryParseJson(value);
  if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed as Record<string, unknown>;
  return null;
}

function stringField(record: Record<string, unknown>, ...keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

/** Pull title/url/summary from a JSON-shaped string when JSON.parse still fails. */
function recoverFieldsFromBlob(text: string): Partial<BackgroundSource> | null {
  if (!looksLikeJsonBlob(text)) return null;
  const title = text.match(/"title"\s*:\s*"((?:\\.|[^"\\])*)"/)?.[1];
  const url = text.match(/"url"\s*:\s*"((?:\\.|[^"\\])*)"/)?.[1];
  const published = text.match(/"published"\s*:\s*"((?:\\.|[^"\\])*)"/)?.[1];
  const extract =
    text.match(/"highlight"\s*:\s*"((?:\\.|[^"\\])*)"/)?.[1] ??
    text.match(/"extract"\s*:\s*"((?:\\.|[^"\\])*)"/)?.[1] ??
    text.match(/"text"\s*:\s*"((?:\\.|[^"\\])*)"/)?.[1];
  if (!title && !url && !extract) return null;
  const unescape = (value: string | undefined) =>
    (value ?? "")
      .replace(/\\n/g, "\n")
      .replace(/\\t/g, " ")
      .replace(/\\"/g, '"')
      .replace(/\\\\/g, "\\");
  return {
    title: title ? unescape(title) : null,
    url: url ? unescape(url) : null,
    published: published ? unescape(published) : null,
    extract: extract ? unescape(extract) : null,
  };
}

function splitResearchBody(text: string): { summary: string; facts: string[] } {
  const normalized = text
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, " ")
    .replace(/\r/g, "")
    .replace(/\u2022/g, "\n- ")
    .trim();
  const lines = normalized
    .split(/\n+/)
    .map((line) => line.replace(/\s+/g, " ").trim())
    .filter(Boolean);

  const facts: string[] = [];
  const prose: string[] = [];
  for (const line of lines) {
    const bullet = line.match(/^[-*•]\s*(.+)$/)?.[1]?.trim();
    if (bullet) {
      if (!facts.some((fact) => fact.toLowerCase() === bullet.toLowerCase())) facts.push(bullet);
      continue;
    }
    // Prefer the longer copy when Exa duplicates highlight + extract.
    const normalizedLine = line.toLowerCase();
    if (prose.some((part) => part.toLowerCase() === normalizedLine)) continue;
    const overlap = prose.findIndex((part) => {
      const other = part.toLowerCase();
      return other.includes(normalizedLine) || normalizedLine.includes(other);
    });
    if (overlap === -1) prose.push(line);
    else if (line.length > (prose[overlap]?.length ?? 0)) prose[overlap] = line;
  }
  return { summary: prose.join("\n\n"), facts };
}

function readableResearchText(value: unknown): { summary: string; facts: string[] } {
  if (value == null) return { summary: "", facts: [] };
  if (typeof value !== "string") return { summary: "", facts: [] };
  const text = value.trim();
  if (!text) return { summary: "", facts: [] };
  if (looksLikeJsonBlob(text)) {
    const recovered = recoverFieldsFromBlob(text);
    if (recovered?.extract) return splitResearchBody(recovered.extract);
  }
  return splitResearchBody(text);
}

function toBackgroundSource(value: unknown): BackgroundSource | null {
  const record = asRecord(value);
  if (record) {
    const url = stringField(record, "url");
    const title = stringField(record, "title");
    const published = stringField(record, "published");
    // Prefer highlight, then extract — they are often duplicates from Exa.
    const highlight = stringField(record, "highlight", "extract", "text", "summary");
    const extractAlt = stringField(record, "extract");
    const rawBody =
      highlight && extractAlt && highlight !== extractAlt && !highlight.includes(extractAlt) && !extractAlt.includes(highlight)
        ? `${highlight}\n${extractAlt}`
        : highlight ?? extractAlt ?? "";
    const { summary, facts } = readableResearchText(rawBody);
    if (title || url || summary || facts.length) {
      return { title, url, published, extract: summary || null, facts };
    }
  }

  if (typeof value === "string") {
    const recovered = recoverFieldsFromBlob(value);
    if (recovered) {
      const { summary, facts } = readableResearchText(recovered.extract ?? "");
      if (recovered.title || recovered.url || summary || facts.length) {
        return {
          title: recovered.title ?? null,
          url: recovered.url ?? null,
          published: recovered.published ?? null,
          extract: summary || null,
          facts,
        };
      }
    }
    const { summary, facts } = readableResearchText(value);
    // Never surface a raw JSON blob as the readable summary.
    if (looksLikeJsonBlob(summary) && !facts.length) return null;
    return summary || facts.length ? { title: null, url: null, published: null, extract: summary || null, facts } : null;
  }
  return null;
}

export function parseBackgroundInfo(value: unknown): BackgroundSource[] {
  if (value == null || value === "") return [];
  if (typeof value === "string") {
    const parsed = tryParseJson(value);
    if (parsed != null) value = parsed;
  }
  const items = Array.isArray(value) ? value : [value];
  return items.map(toBackgroundSource).filter((item): item is BackgroundSource => Boolean(item));
}

export function sourceHostname(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}
