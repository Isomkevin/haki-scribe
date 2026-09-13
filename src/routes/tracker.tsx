import { createFileRoute } from "@tanstack/react-router";
import { TrackerPage } from "@/components/hakiscribe/tracker";

export const Route = createFileRoute("/tracker")({
  head: () => ({
    meta: [
      { title: "Case Tracker — HakiScribe" },
      {
        name: "description",
        content:
          "Track every recorded legal session: dates, flagged moments, drafted documents and upcoming court and client appointments.",
      },
      { property: "og:title", content: "Case Tracker — HakiScribe" },
      {
        property: "og:description",
        content: "All matters, flags, drafted documents and upcoming dates in one continuously updating view.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: TrackerPage,
});
