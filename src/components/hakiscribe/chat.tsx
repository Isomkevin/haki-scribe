import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Loader2, MessageSquarePlus, Scale, SendHorizonal, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { friendlyErrorMessage, hakiApi, type ChatMessage, type ChatThread } from "@/lib/hakiscribe";
import { PageShell } from "./shell";

const SUGGESTIONS = [
  "Summarise this meeting for the partner in five bullet points.",
  "List every commitment my client made and its deadline.",
  "What should I ask at the next mention?",
];

export function ChatPage({ sessionId, threadId }: { sessionId: string; threadId: string }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const threads = useQuery({ queryKey: ["chats", sessionId], queryFn: () => hakiApi.listChats(sessionId) });
  const thread = useQuery({ queryKey: ["chat", sessionId, threadId], queryFn: () => hakiApi.getChat(sessionId, threadId) });
  const catalogue = useQuery({ queryKey: ["models"], queryFn: hakiApi.listModels, retry: false });
  const [model, setModel] = useState("");
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<ChatMessage | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const createThread = useMutation({
    mutationFn: () => hakiApi.createChat(sessionId),
    onSuccess: (created) => {
      void queryClient.invalidateQueries({ queryKey: ["chats", sessionId] });
      void navigate({ to: "/sessions/$sessionId/chat/$threadId", params: { sessionId, threadId: created.id } });
    },
  });
  const deleteThread = useMutation({
    mutationFn: (id: string) => hakiApi.deleteChat(sessionId, id),
    onSuccess: async (_r, id) => {
      const rest = (await queryClient.fetchQuery({ queryKey: ["chats", sessionId], queryFn: () => hakiApi.listChats(sessionId) })).filter((t) => t.id !== id);
      if (id !== threadId) return;
      if (rest[0]) void navigate({ to: "/sessions/$sessionId/chat/$threadId", params: { sessionId, threadId: rest[0].id } });
      else createThread.mutate();
    },
  });
  const send = useMutation({
    mutationFn: (content: string) => hakiApi.sendChatMessage(sessionId, threadId, { content, ...(model ? { model } : {}) }),
    onMutate: (content) => {
      setPending({ id: "pending", role: "user", content, created_at: new Date().toISOString() });
      setDraft("");
    },
    onSuccess: (updated: ChatThread) => {
      queryClient.setQueryData(["chat", sessionId, threadId], updated);
      void queryClient.invalidateQueries({ queryKey: ["chats", sessionId] });
    },
    onSettled: () => {
      setPending(null);
      inputRef.current?.focus();
    },
  });

  useEffect(() => {
    inputRef.current?.focus();
  }, [threadId]);

  const messages = [...(thread.data?.messages ?? []), ...(pending ? [pending] : [])];
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, send.isPending]);

  const submit = () => {
    const content = draft.trim();
    if (!content || send.isPending) return;
    send.mutate(content);
  };

  return (
    <PageShell>
      <div className="mb-4 flex items-center justify-between gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link to="/sessions/$sessionId" params={{ sessionId }} search={{ fresh: false }}>
            <ArrowLeft className="size-4" /> Back to session
          </Link>
        </Button>
        <Button size="sm" variant="outline" onClick={() => createThread.mutate()} disabled={createThread.isPending}>
          <MessageSquarePlus className="size-4" /> New conversation
        </Button>
      </div>
      <div className="grid gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="rounded-lg border border-border bg-card p-2">
          <p className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Conversations</p>
          <ul className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
            {(threads.data ?? []).map((item) => (
              <li key={item.id} className={`flex min-w-44 items-center rounded-md lg:min-w-0 ${item.id === threadId ? "bg-secondary" : "hover:bg-muted"}`}>
                <Link
                  to="/sessions/$sessionId/chat/$threadId"
                  params={{ sessionId, threadId: item.id }}
                  className="min-w-0 flex-1 truncate px-2 py-2 text-sm"
                >
                  {item.title}
                </Link>
                <button
                  type="button"
                  aria-label={`Delete ${item.title}`}
                  className="p-2 text-muted-foreground hover:text-destructive"
                  onClick={() => deleteThread.mutate(item.id)}
                >
                  <Trash2 className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <section className="flex min-h-[70svh] flex-col rounded-lg border border-border bg-card">
          <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
            <div className="flex min-w-0 items-center gap-2">
              <span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground"><Scale className="size-4" /></span>
              <div className="min-w-0">
                <p className="truncate font-serif font-semibold">{thread.data?.title ?? "Conversation"}</p>
                <p className="text-[11px] text-muted-foreground">Uses the verified record only — locked lines are never sent.</p>
              </div>
            </div>
            <select
              aria-label="AI model"
              className="rounded-md border border-border bg-background px-2 py-1.5 text-xs"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            >
              <option value="">Default{catalogue.data?.default ? ` (${catalogue.data.default})` : ""}</option>
              {(catalogue.data?.models ?? []).map((m) => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </select>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5">
            {thread.isLoading ? <p className="text-sm text-muted-foreground">Loading conversation…</p> : null}
            {thread.isError ? <p className="text-sm text-destructive">{friendlyErrorMessage(thread.error)}</p> : null}
            {!thread.isLoading && messages.length === 0 ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Ask about this session. The model remembers the whole conversation.</p>
                <div className="flex flex-wrap gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} type="button" onClick={() => send.mutate(s)} className="rounded-full border border-border px-3 py-1.5 text-left text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
            {messages.map((m) =>
              m.role === "user" ? (
                <div key={m.id} className="ml-auto max-w-[85%] whitespace-pre-wrap rounded-lg bg-primary px-3.5 py-2.5 text-sm text-primary-foreground">
                  {m.content}
                </div>
              ) : (
                <div key={m.id} className={`max-w-[92%] text-sm leading-6 ${m.error ? "rounded-md border border-destructive/30 bg-destructive/5 p-3 text-destructive" : "text-foreground"}`}>
                  <div className="prose prose-sm max-w-none [&_li]:my-0.5 [&_p]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5">
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                  </div>
                  {m.model ? <p className="mt-1 text-[10px] text-muted-foreground">{m.model}</p> : null}
                </div>
              ),
            )}
            {send.isPending ? (
              <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-3.5 animate-spin" /> Thinking…</p>
            ) : null}
            {send.isError ? <p className="text-sm text-destructive">{friendlyErrorMessage(send.error)}</p> : null}
            <div ref={endRef} />
          </div>

          <div className="border-t border-border p-3">
            <div className="flex items-end gap-2">
              <Textarea
                ref={inputRef}
                aria-label="Message"
                className="min-h-12 flex-1 resize-none bg-background"
                placeholder="Ask a follow-up…"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                  }
                }}
              />
              <Button size="icon" className="size-11 shrink-0" aria-label="Send" disabled={!draft.trim() || send.isPending} onClick={submit}>
                <SendHorizonal className="size-4" />
              </Button>
            </div>
          </div>
        </section>
      </div>
    </PageShell>
  );
}

/** Opens the latest conversation for a session, or starts one. */
export function ChatLauncher({ sessionId }: { sessionId: string }) {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const list = await hakiApi.listChats(sessionId);
        const target = list[0] ?? (await hakiApi.createChat(sessionId));
        if (!cancelled) void navigate({ to: "/sessions/$sessionId/chat/$threadId", params: { sessionId, threadId: target.id }, replace: true });
      } catch (caught) {
        if (!cancelled) setError(friendlyErrorMessage(caught));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId, navigate]);
  return (
    <PageShell>
      <p className="text-sm text-muted-foreground">{error ?? "Opening conversation…"}</p>
    </PageShell>
  );
}
