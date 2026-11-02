import { createFileRoute } from "@tanstack/react-router";
import { TrustPage } from "@/components/hakiscribe/trust-page";
import { absoluteUrl } from "@/lib/site";
import { CONTACT_COPY } from "@/lib/trust-pages";

export const Route = createFileRoute("/contact")({
  head: () => ({
    meta: [
      { title: "Contact — HakiScribe" },
      {
        name: "description",
        content:
          "Contact HakiChain in Nairobi about HakiScribe product, deployment, and privacy questions.",
      },
      { property: "og:title", content: "Contact — HakiScribe" },
      {
        property: "og:description",
        content: "Reach HakiChain about HakiScribe through the organization site.",
      },
      { property: "og:type", content: "website" },
      { property: "og:url", content: absoluteUrl("/contact") },
      { property: "og:image", content: absoluteUrl("/og-image.png") },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:image", content: absoluteUrl("/og-image.png") },
    ],
    links: [{ rel: "canonical", href: absoluteUrl("/contact") }],
  }),
  component: ContactPage,
});

function ContactPage() {
  return <TrustPage copy={CONTACT_COPY} />;
}
