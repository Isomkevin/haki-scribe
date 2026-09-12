import { task } from "@trigger.dev/sdk";

// Thin relay — see detectActions.ts for the pattern. Real execution
// logic (drafting, Ambiguous AI calls, matter linking) lives in the
// Python backend's action_executor.py, called via /internal/generate.

type GenerateActionsPayload = {
  actions: Record<string, unknown>[];
};

export const generateActions = task({
  id: "generate-actions",
  run: async (payload: GenerateActionsPayload) => {
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
