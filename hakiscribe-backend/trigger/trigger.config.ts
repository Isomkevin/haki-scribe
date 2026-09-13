import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { syncEnvVars } from "@trigger.dev/build/extensions/core";
import { defineConfig } from "@trigger.dev/sdk";

function backendRelayEnv(): Record<string, string> {
  const values: Record<string, string> = {
    BACKEND_INTERNAL_URL: "https://hakiscribe-backend.onrender.com",
  };
  const localPath = resolve(process.cwd(), "../.env.local");
  if (!existsSync(localPath)) {
    return values;
  }
  for (const raw of readFileSync(localPath, "utf8").split("\n")) {
    const line = raw.split("#", 1)[0].trim();
    if (!line.includes("=")) {
      continue;
    }
    const [key, ...rest] = line.split("=");
    const name = key.trim();
    const value = rest.join("=").trim().replace(/^['"]|['"]$/g, "");
    if (name === "BACKEND_INTERNAL_URL" && value) {
      values.BACKEND_INTERNAL_URL = value;
    }
    if (name === "BACKEND_INTERNAL_SECRET" && value) {
      values.BACKEND_INTERNAL_SECRET = value;
    }
  }
  return values;
}

export default defineConfig({
  project: "proj_hobqixzcvyknoigffkjq",
  dirs: ["./"],
  // Required by Trigger.dev 4.x — must be at least 5 seconds.
  // Matches the 10-minute cap already set on research/generate tasks.
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
    extensions: [syncEnvVars(async () => backendRelayEnv())],
  },
});
