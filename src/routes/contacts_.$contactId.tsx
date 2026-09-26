import { createFileRoute } from "@tanstack/react-router";
import { RequireAuth } from "@/components/hakiscribe/auth-gate";
import { ContactProfilePage } from "@/components/hakiscribe/contact-profile";

export const Route = createFileRoute("/contacts_/$contactId")({
  head: () => ({
    meta: [
      { title: "Contact profile — HakiScribe" },
      { name: "description", content: "Every session, drafted document and diary entry a contact appears in, with editable details." },
      { property: "og:title", content: "Contact profile — HakiScribe" },
      { property: "og:description", content: "One person's full record across your HakiScribe matters." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ContactProfileRoute,
});

function ContactProfileRoute() {
  const { contactId } = Route.useParams();
  return (
    <RequireAuth>
      <ContactProfilePage contactId={contactId} />
    </RequireAuth>
  );
}
