import { createFileRoute } from "@tanstack/react-router";
import { ConnectorsPage } from "@/components/hakiscribe/connectors";

export const Route = createFileRoute("/connectors")({
  head: () => ({
    meta: [
      { title: "Connectors — HakiScribe" },
      {
        name: "description",
        content:
          "Link HakiScribe to Claude, OpenAI, Gemini, Google Drive, Dropbox, HakiChain and other legal tools your practice uses.",
      },
      { property: "og:title", content: "Connectors — HakiScribe" },
      {
        property: "og:description",
        content: "Connect your own AI keys and storage so drafted documents, research and calendar events flow to where your practice lives.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ConnectorsPage,
});
