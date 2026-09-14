import { createFileRoute } from "@tanstack/react-router";
import { RequireAuth } from "@/components/hakiscribe/auth-gate";
import { z } from "zod";
import { ResearchPage } from "@/components/hakiscribe/research";

export const Route = createFileRoute("/research")({
  validateSearch: z.object({ session: z.string().optional() }),
  head: () => ({
    meta: [
      { title: "Kenyan Legal Research — HakiScribe" },
      {
        name: "description",
        content:
          "Turn a recorded legal conversation into cited Kenyan case law, statutes and precedent, grounded in the verified transcript.",
      },
      { property: "og:title", content: "Kenyan Legal Research — HakiScribe" },
      {
        property: "og:description",
        content: "Cited Kenyan authorities for the issues actually raised in your session transcript.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ResearchRoute,
});

function ResearchRoute() {
  const { session } = Route.useSearch();
  return <ResearchPage {...(session ? { sessionId: session } : {})} />;
}
