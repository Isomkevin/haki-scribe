import { createFileRoute } from "@tanstack/react-router";
import { TrustPage } from "@/components/hakiscribe/trust-page";
import { absoluteUrl } from "@/lib/site";
import { ABOUT_COPY } from "@/lib/trust-pages";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "About — HakiScribe" },
      {
        name: "description",
        content:
          "HakiScribe is HakiChain’s private listening companion for source-traceable legal work in Kenyan practice.",
      },
      { property: "og:title", content: "About — HakiScribe" },
      {
        property: "og:description",
        content: "Learn how HakiScribe turns verified conversations into reviewed legal work.",
      },
      { property: "og:type", content: "website" },
      { property: "og:url", content: absoluteUrl("/about") },
      { property: "og:image", content: absoluteUrl("/og-image.png") },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:image", content: absoluteUrl("/og-image.png") },
    ],
    links: [{ rel: "canonical", href: absoluteUrl("/about") }],
  }),
  component: AboutPage,
});

function AboutPage() {
  return <TrustPage copy={ABOUT_COPY} />;
}
