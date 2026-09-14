import { createFileRoute } from "@tanstack/react-router";
import { LandingPage } from "@/components/hakiscribe/app";

export const Route = createFileRoute("/")({
  head: () => ({ meta: [
    { title: "HakiScribe — Conversation to Legal Work" },
    { name: "description", content: "A private legal work companion for source-traceable documents, follow-ups, matters, notes, and time entries." },
    { property: "og:title", content: "HakiScribe — Conversation to Legal Work" },
    { property: "og:description", content: "A trusted legal companion that turns verified conversations into ready-to-review work." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: LandingPage,
});
