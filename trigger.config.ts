import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { syncEnvVars } from "@trigger.dev/build/extensions/core";
import { defineConfig } from "@trigger.dev/sdk";

function readEnvFile(path: string): Record<string, string> {
  if (!existsSync(path)) {
    return {};
  }
  const values: Record<string, string> = {};
  for (const raw of readFileSync(path, "utf8").split("\n")) {
    const line = (raw.split("#", 1)[0] ?? "").trim();
    if (!line.includes("=")) {
      continue;
    }
    const [key, ...rest] = line.split("=");
    const name = (key ?? "").trim();
    const value = rest.join("=").trim().replace(/^['"]|['"]$/g, "");
    if (name && value) {
      values[name] = value;
    }
  }
  return values;
}

/** Relay env for Trigger cloud → Render FastAPI /internal/* endpoints. */
function backendRelayEnv(): Record<string, string> {
  const rootEnv = readEnvFile(resolve(process.cwd(), ".env.local"));
  const backendEnv = readEnvFile(resolve(process.cwd(), "hakiscribe-backend/.env.local"));
  const merged = { ...backendEnv, ...rootEnv };
  const values: Record<string, string> = {
    BACKEND_INTERNAL_URL:
      merged.BACKEND_INTERNAL_URL || "https://hakiscribe-backend.onrender.com",
  };
  // Never sync an empty secret — that would wipe a valid dashboard value.
  if (merged.BACKEND_INTERNAL_SECRET) {
    values.BACKEND_INTERNAL_SECRET = merged.BACKEND_INTERNAL_SECRET;
  }
  return values;
}

export default defineConfig({
  project: "proj_hobqixzcvyknoigffkjq",
  dirs: ["./src/trigger"],
  maxDuration: 600,
  retries: {
    enabledInDev: true,
    default: {
      maxAttempts: 3,
      minTimeoutInMs: 1000,
      maxTimeoutInMs: 10000,
      factor: 2,
    },
  },
  build: {
    // Keeps prod env in sync with local .env.local on every deploy.
    extensions: [syncEnvVars(async () => backendRelayEnv())],
  },
});
