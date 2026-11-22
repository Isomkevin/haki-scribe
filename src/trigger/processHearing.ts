import { task } from "@trigger.dev/sdk";

// Thin relay: hearing ASR + proceedings live in the Python backend
// (`hearing_pipeline.process_hearing`), called via /internal/process-hearing.
// Durable retries survive worker restart; local_only never enqueues this task.

type ProcessHearingPayload = {
  hearing_id: string;
  organisation_id?: string;
  workspace_id?: string;
  user_id?: string;
  use_llm?: boolean;
  diarize?: boolean;
  language_hint?: string | null;
};

export const processHearing = task({
  id: "process-hearing",
  maxDuration: 900,
  retry: {
    maxAttempts: 2,
  },
  run: async (payload: ProcessHearingPayload) => {
    const backendUrl = process.env["BACKEND_INTERNAL_URL"];
    if (!backendUrl) {
      throw new Error("BACKEND_INTERNAL_URL is not set");
    }
    if (!process.env["BACKEND_INTERNAL_SECRET"]) {
      throw new Error("BACKEND_INTERNAL_SECRET is not set");
    }

    const response = await fetch(`${backendUrl}/internal/process-hearing`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Secret": process.env["BACKEND_INTERNAL_SECRET"],
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(880_000),
    });

    if (!response.ok) {
      throw new Error(`Backend /internal/process-hearing failed: ${response.status} ${await response.text()}`);
    }

    return await response.json();
  },
});
