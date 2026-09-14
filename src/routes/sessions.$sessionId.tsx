import { createFileRoute } from "@tanstack/react-router";
import { RequireAuth } from "@/components/hakiscribe/auth-gate";
import { z } from "zod";
import { SessionPage } from "@/components/hakiscribe/app";

export const Route = createFileRoute("/sessions/$sessionId")({
  validateSearch: z.object({ fresh: z.coerce.boolean().optional().default(false) }),
  head: () => ({ meta: [
    { title: "Secure Session — HakiScribe" },
    { name: "description", content: "Verify a legal conversation and prepare source-traceable legal work." },
    { property: "og:title", content: "Secure Session — HakiScribe" },
    { property: "og:description", content: "Review and generate legal work from a verified HakiScribe session." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: SessionRoute,
});

function SessionRoute() {
  const { sessionId } = Route.useParams();
  const { fresh } = Route.useSearch();
  return <SessionPage sessionId={sessionId} fresh={fresh} />;
}