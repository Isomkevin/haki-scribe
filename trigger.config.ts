import { defineConfig } from "@trigger.dev/sdk";

export default defineConfig({
  project: "proj_hobqixzcvyknoigffkjq",
  dirs: ["./src/trigger"],
  maxDuration: 3600,
  retries: {
    enabledInDev: true,
    default: {
      maxAttempts: 3,
      minTimeoutInMs: 1000,
      maxTimeoutInMs: 10000,
      factor: 2,
    },
  },
});
