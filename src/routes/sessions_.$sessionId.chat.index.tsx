import { createFileRoute } from "@tanstack/react-router";
import { RequireAuth } from "@/components/hakiscribe/auth-gate";
import { ChatLauncher } from "@/components/hakiscribe/chat";

export const Route = createFileRoute("/sessions_/$sessionId/chat/")({
  head: () => ({
    meta: [
      { title: "Open Session Chat — HakiScribe" },
      { name: "description", content: "Open the latest AI conversation for this session." },
      { property: "og:title", content: "Open Session Chat — HakiScribe" },
      { property: "og:description", content: "Continue an AI conversation about a verified session." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: LauncherRoute,
});

function LauncherRoute() {
  const { sessionId } = Route.useParams();
  return (
    <RequireAuth>
      <ChatLauncher sessionId={sessionId} />
    </RequireAuth>
  );
}
