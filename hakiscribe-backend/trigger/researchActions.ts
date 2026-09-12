import { task } from "@trigger.dev/sdk";

// Thin relay for the slower transcript work — legal research (Exa
// retrieval + model synthesis), open-web background checks, and
// free-form "ask any model" instructions. The logic lives in the Python
// backend's action_executor.py, reached via /internal/generate; this
// task exists so the retrieval + model round-trip runs durably with
// retries instead of holding an HTTP request open.

type ResearchActionsPayload = {
  actions: Record<string, unknown>[];
  transcript?: Record<string, unknown>[];
};

export const researchActions = task({
  id: "research-actions",
  maxDuration: 600,
  run: async (payload: ResearchActionsPayload) => {
    const backendUrl = process.env.BACKEND_INTERNAL_URL;
    if (!backendUrl) {
      throw new Error("BACKEND_INTERNAL_URL is not set");
    }

    const response = await fetch(`${backendUrl}/internal/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Secret": process.env.BACKEND_INTERNAL_SECRET ?? "",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Backend /internal/generate failed: ${response.status} ${await response.text()}`);
    }

    return await response.json();
  },
});
