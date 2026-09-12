export type SessionSource = "mic" | "omi";
export type SessionStatus = "recording" | "processing" | "ready" | "exported";
export type ActionType =
  | "draft_document"
  | "calendar_event"
  | "workspace_matter"
  | "crm_entry"
  | "private_note"
  | "time_entry";

export interface Session {
  id: string;
  title: string;
  source: SessionSource;
  language_hint: string | null;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
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
}

export interface SessionDetail extends Session {
  transcript: TranscriptSegment[];
  detected_actions: DetectedAction[];
  flagged_moments: FlaggedMoment[];
  action_results?: ActionResult[];
}

export interface Matter {
  id: string;
  client_name: string;
  matter_name: string;
  created_at: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
  }
}

const configuredBaseUrl = (import.meta.env["VITE_API_BASE_URL"] as string | undefined)?.replace(
  /\/$/,
  "",
);

export const hasApiConfiguration = Boolean(configuredBaseUrl);

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
  finalize: (id: string) => request<Session>(`/sessions/${id}/finalize`, { method: "POST" }),
  detect: (id: string) => request<DetectedAction[]>(`/sessions/${id}/detect`, { method: "POST" }),
  listActions: (id: string) => request<DetectedAction[]>(`/sessions/${id}/actions`),
  generate: (id: string, actionIds: string[]) =>
    request<ActionResult[]>(`/sessions/${id}/generate`, {
      method: "POST",
      body: JSON.stringify({ action_ids: actionIds }),
    }),
  listMatters: () => request<Matter[]>("/matters"),
  createMatter: (body: { client_name: string; matter_name: string }) =>
    request<Matter>("/matters", { method: "POST", body: JSON.stringify(body) }),
  health: () => request<{ status: string }>("/health"),
};

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