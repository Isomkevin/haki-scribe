import { createFileRoute } from "@tanstack/react-router";
import { RequireAuth } from "@/components/hakiscribe/auth-gate";
import { z } from "zod";
import { SettingsPage } from "@/components/hakiscribe/settings";
import { SETTINGS_SECTIONS } from "@/lib/workspace-settings";

export const Route = createFileRoute("/settings")({
  validateSearch: z.object({
    section: z.enum(SETTINGS_SECTIONS).optional(),
  }),
  head: () => ({
    meta: [
      { title: "Settings — HakiScribe" },
      {
        name: "description",
        content:
          "Profile, security, connectors and workspace defaults for the HakiScribe private practice workspace.",
      },
      { property: "og:title", content: "Settings — HakiScribe" },
      {
        property: "og:description",
        content: "Configure profile, security, and the tools your practice already uses. Credentials stay on the server.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: SettingsRoute,
});

function SettingsRoute() {
  const { section } = Route.useSearch();
  return <SettingsPage section={section ?? "profile"} />;
}
