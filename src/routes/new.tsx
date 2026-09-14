import { createFileRoute } from "@tanstack/react-router";
import { RequireAuth } from "@/components/hakiscribe/auth-gate";
import { NewSessionPage } from "@/components/hakiscribe/app";

export const Route = createFileRoute("/new")({
  head: () => ({
    meta: [
      { title: "Start a Session — HakiScribe" },
      { name: "description", content: "Open a private HakiScribe session or return to secure legal work already in progress." },
      { property: "og:title", content: "Start a Session — HakiScribe" },
      { property: "og:description", content: "Open the private HakiScribe workspace for recording and legal work." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: NewRoute,
});

function NewRoute() {
  return (
    <RequireAuth>
      <NewSessionPage />
    </RequireAuth>
  );
}
