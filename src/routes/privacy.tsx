import { createFileRoute } from "@tanstack/react-router";
import { TrustPage } from "@/components/hakiscribe/trust-page";
import { absoluteUrl } from "@/lib/site";
import { PRIVACY_COPY } from "@/lib/trust-pages";

export const Route = createFileRoute("/privacy")({
  head: () => ({
    meta: [
      { title: "Privacy — HakiScribe" },
      {
        name: "description",
        content:
          "How HakiScribe handles privilege, workspace-scoped records, and Kenya Data Protection Act alignment in progress.",
      },
      { property: "og:title", content: "Privacy — HakiScribe" },
      {
        property: "og:description",
        content: "Privilege-first processing and human approval before work leaves HakiScribe.",
      },
      { property: "og:type", content: "website" },
      { property: "og:url", content: absoluteUrl("/privacy") },
      { property: "og:image", content: absoluteUrl("/og-image.png") },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:image", content: absoluteUrl("/og-image.png") },
    ],
    links: [{ rel: "canonical", href: absoluteUrl("/privacy") }],
  }),
  component: PrivacyPage,
});

function PrivacyPage() {
  return <TrustPage copy={PRIVACY_COPY} />;
}
