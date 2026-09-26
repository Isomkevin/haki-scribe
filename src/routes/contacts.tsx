import { createFileRoute } from "@tanstack/react-router";
import { RequireAuth } from "@/components/hakiscribe/auth-gate";
import { ContactsPage } from "@/components/hakiscribe/contacts";

export const Route = createFileRoute("/contacts")({
  head: () => ({
    meta: [
      { title: "Contacts — HakiScribe" },
      { name: "description", content: "A directory of every client, witness and counsel across your HakiScribe matters." },
      { property: "og:title", content: "Contacts — HakiScribe" },
      { property: "og:description", content: "Search every contact from all matters, open their matter, and add new people quickly." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: () => (
    <RequireAuth>
      <ContactsPage />
    </RequireAuth>
  ),
});
