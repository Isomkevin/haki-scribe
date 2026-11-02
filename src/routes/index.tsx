import { createFileRoute } from "@tanstack/react-router";
import { LandingPage } from "@/components/hakiscribe/app";
import { absoluteUrl, SITE_CONTACT, SITE_ORIGIN } from "@/lib/site";

const homepageJsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SoftwareApplication",
      name: "HakiScribe",
      description:
        "A private legal work companion that turns verified conversations into source-traceable documents, follow-ups, matters, notes, and time entries.",
      url: SITE_ORIGIN,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      author: {
        "@type": "Organization",
        name: SITE_CONTACT.organization,
        url: SITE_CONTACT.web,
      },
      publisher: {
        "@type": "Organization",
        name: SITE_CONTACT.organization,
        url: SITE_CONTACT.web,
      },
    },
    {
      "@type": "Organization",
      name: SITE_CONTACT.organization,
      url: SITE_CONTACT.web,
      sameAs: [SITE_CONTACT.web, SITE_CONTACT.github],
      address: {
        "@type": "PostalAddress",
        addressLocality: "Nairobi",
        addressCountry: "KE",
      },
    },
    {
      "@type": "WebSite",
      name: "HakiScribe",
      url: SITE_ORIGIN,
      description:
        "Conversation to legal work — privilege-aware capture for Kenyan practice.",
      publisher: {
        "@type": "Organization",
        name: SITE_CONTACT.organization,
        url: SITE_CONTACT.web,
      },
    },
  ],
};

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "HakiScribe — Conversation to Legal Work" },
      {
        name: "description",
        content:
          "A private legal work companion for source-traceable documents, follow-ups, matters, notes, and time entries.",
      },
      { property: "og:title", content: "HakiScribe — Conversation to Legal Work" },
      {
        property: "og:description",
        content: "A trusted legal companion that turns verified conversations into ready-to-review work.",
      },
      { property: "og:type", content: "website" },
      { property: "og:url", content: absoluteUrl("/") },
      { property: "og:image", content: absoluteUrl("/og-image.png") },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:image", content: absoluteUrl("/og-image.png") },
    ],
    links: [{ rel: "canonical", href: absoluteUrl("/") }],
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify(homepageJsonLd),
      },
    ],
  }),
  component: LandingPage,
});
