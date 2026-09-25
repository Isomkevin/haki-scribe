import { createFileRoute } from "@tanstack/react-router";
import { RequireAuth } from "@/components/hakiscribe/auth-gate";
import { OmiGuidePage } from "@/components/hakiscribe/omi-guide";

export const Route = createFileRoute("/omi")({
  head: () => ({
    meta: [
      { title: "Omi Wearable Setup — HakiScribe" },
      { name: "description", content: "Step-by-step setup and pairing for the Omi wearable with HakiScribe." },
      { property: "og:title", content: "Omi Wearable Setup — HakiScribe" },
      { property: "og:description", content: "Pair Omi for live transcription and import past conversations." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: () => (
    <RequireAuth>
      <OmiGuidePage />
    </RequireAuth>
  ),
});
