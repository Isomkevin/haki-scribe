import { task } from "@trigger.dev/sdk";

// Thin relay: hearing ASR + proceedings live in the Python backend
// (`hearing_jobs.run_job`), called via /internal/process-hearing. The backend
// only uses this when its own job worker is off (HAKISCRIBE_JOB_WORKER=false);
// the job row is the source of truth, so a retry after the backend already
// claimed or finished the job returns `not_claimed` instead of running twice.
// local_only never enqueues this task.

type ProcessHearingPayload = {
  job_id: string;
  hearing_id: string;
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
