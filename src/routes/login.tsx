import { createFileRoute } from "@tanstack/react-router";
import { LoginPage } from "@/components/hakiscribe/login";

export const Route = createFileRoute("/login")({
  validateSearch: (search: Record<string, unknown>) => ({
    next: typeof search['next'] === "string" ? (search['next'] as string) : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Sign in — HakiScribe" },
      {
        name: "description",
        content: "Sign in to the private HakiScribe workspace for recordings, transcripts and drafted legal documents.",
      },
      { property: "og:title", content: "Sign in — HakiScribe" },
      { property: "og:description", content: "Private sign-in for the HakiScribe legal workspace." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: LoginRoute,
});

function LoginRoute() {
  const { next } = Route.useSearch();
  return <LoginPage next={next} />;
}
