import { task } from "@trigger.dev/sdk";

// Thin relay: the real detection logic (LLM prompt, source-grounding,
// matter-continuity lookup) lives in the Python backend's
// action_detector.py, called via /internal/detect. This task exists so
// detection runs as a durable, retried background job instead of a
// blocking HTTP call from the frontend's perspective.
//
// BACKEND_INTERNAL_URL must be a URL Trigger.dev's cloud can reach —
// not localhost. Use a tunnel (ngrok) for local dev, a real deploy for
// anything beyond that.

type DetectActionsPayload = {
  session_id: string;
  transcript: Record<string, unknown>[];
  flags: Record<string, unknown>[];
  known_matters: Record<string, unknown>[];
};

export const detectActions = task({
  id: "detect-actions",
  // Model detection + Exa enrichment can take a couple of minutes.
  maxDuration: 300,
  retry: {
    maxAttempts: 3,
  },
  run: async (payload: DetectActionsPayload) => {
    const backendUrl = process.env['BACKEND_INTERNAL_URL'];
    if (!backendUrl) {
      throw new Error("BACKEND_INTERNAL_URL is not set");
    }
    if (!process.env['BACKEND_INTERNAL_SECRET']) {
      throw new Error("BACKEND_INTERNAL_SECRET is not set");
    }

    const response = await fetch(`${backendUrl}/internal/detect`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Secret": process.env['BACKEND_INTERNAL_SECRET'],
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(280_000),
    });

    if (!response.ok) {
      throw new Error(`Backend /internal/detect failed: ${response.status} ${await response.text()}`);
    }

    return await response.json();
  },
});
