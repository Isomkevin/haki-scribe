import { createFileRoute } from "@tanstack/react-router";
import { RequireAuth } from "@/components/hakiscribe/auth-gate";
import { ChatPage } from "@/components/hakiscribe/chat";

export const Route = createFileRoute("/sessions_/$sessionId/chat/$threadId")({
  head: () => ({
    meta: [
      { title: "Session Chat — HakiScribe" },
      { name: "description", content: "Converse with your chosen AI model about a verified legal session." },
      { property: "og:title", content: "Session Chat — HakiScribe" },
      { property: "og:description", content: "Threaded AI conversations grounded in the verified transcript." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: ChatRoute,
});

function ChatRoute() {
  const { sessionId, threadId } = Route.useParams();
  return (
    <RequireAuth>
      <ChatPage key={threadId} sessionId={sessionId} threadId={threadId} />
    </RequireAuth>
  );
}
