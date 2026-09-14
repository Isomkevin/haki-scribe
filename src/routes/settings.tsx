import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "@/components/hakiscribe/settings";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — HakiScribe" },
      {
        name: "description",
        content:
          "Configure HakiScribe connectors, keys and workspace tools so drafted work can reach the systems your practice already uses.",
      },
      { property: "og:title", content: "Settings — HakiScribe" },
      {
        property: "og:description",
        content: "Connect AI, storage and practice tools from workspace settings. Credentials stay on the server.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: SettingsPage,
});
