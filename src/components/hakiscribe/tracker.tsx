import { useQueries, useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { CalendarClock, ExternalLink, FileText, Flag, RefreshCw, Scale } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useDemoMode } from "@/hooks/use-demo-mode";
import { filterDemoSessions } from "@/lib/demo-mode";
import { hakiApi, friendlyErrorMessage, type ActionResult, type SessionDetail } from "@/lib/hakiscribe";
import { PageShell, SectionHeading, SourceIcon, StatusBadge, WorkspaceFooter } from "./shell";
import { TrustLine } from "./brand";

const REFRESH_MS = 20_000;

interface TrackedDocument {
  sessionId: string;
  sessionTitle: string;
  kind: string;
  url: string | null;
  createdAt: string | null;
  archived: boolean;
}

interface TrackedEvent {
  sessionId: string;
  sessionTitle: string;
  title: string;
  start: string | null;
  location: string | null;
  attendees: string[];
}

function str(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function documentOf(result: ActionResult, detail: SessionDetail): TrackedDocument | null {
  if (result.type !== "draft_document" || result.status !== "success") return null;
  const kind = str(result.result["document_kind"]) ?? "Legal document";
  return {
    sessionId: detail.id,
    sessionTitle: detail.title,
    kind: kind.replace(/[-_]/g, " "),
    url: str(result.result["ambiguous_document_url"]) ?? str(result.result["s3_url"]),
    createdAt: str(result.created_at ?? null) ?? detail.created_at,
    archived: Boolean(str(result.result["s3_url"])),
  };
}

function eventOf(result: ActionResult, detail: SessionDetail): TrackedEvent | null {
  if (result.type !== "calendar_event" || result.status !== "success") return null;
  const attendees = Array.isArray(result.result["attendees"])
    ? (result.result["attendees"] as unknown[]).map((item) => String(item))
    : [];
  return {
    sessionId: detail.id,
    sessionTitle: detail.title,
    title: str(result.result["title"]) ?? "Scheduled matter",
    start: str(result.result["start"]),
    location: str(result.result["location"]),
    attendees,
  };
}

function formatDate(value: string | null) {
  if (!value) return "Date not on the record";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-KE", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDay(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-KE", { day: "numeric", month: "short", year: "numeric" });
}

export function TrackerPage() {
  const { enabled: demoDataEnabled } = useDemoMode();
  const sessions = useQuery({
    queryKey: ["sessions", { includeDemo: demoDataEnabled }],
    queryFn: () => hakiApi.listSessions({ includeDemo: demoDataEnabled }),
    refetchInterval: REFRESH_MS,
    retry: false,
  });

  const librarySessions = filterDemoSessions(sessions.data ?? [], demoDataEnabled);

  const details = useQueries({
    queries: librarySessions.map((session) => ({
      queryKey: ["session", session.id],
      queryFn: () => hakiApi.getSession(session.id),
      refetchInterval: REFRESH_MS,
      retry: false,
    })),
  });

  const loaded = details
    .map((query) => query.data)
    .filter((value): value is SessionDetail => Boolean(value))
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  const documents: TrackedDocument[] = [];
  const events: TrackedEvent[] = [];
  let flagCount = 0;
  for (const detail of loaded) {
    flagCount += detail.flagged_moments.length;
    for (const result of detail.action_results ?? []) {
      const document = documentOf(result, detail);
      if (document) documents.push(document);
      const event = eventOf(result, detail);
      if (event) events.push(event);
    }
  }

  const now = Date.now();
  const upcoming = events
    .filter((event) => event.start && new Date(event.start).getTime() >= now)
    .sort((a, b) => new Date(a.start ?? 0).getTime() - new Date(b.start ?? 0).getTime());

  const refreshing = sessions.isFetching || details.some((query) => query.isFetching);

  return (
    <PageShell back>
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">
        <header className="mb-7 border-b border-border pb-7 sm:mb-8 sm:pb-8">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Case tracker</p>
          <h1 className="mt-2 max-w-3xl font-serif text-3xl font-semibold leading-tight sm:text-4xl">
            Every matter on the record, and what is coming next
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
            Dates, flagged moments, drafted documents and scheduled appearances across all your sessions. The page
            refreshes itself, so it keeps pace as new artifacts are generated.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Badge variant="outline" className="gap-1.5">
              <RefreshCw className={refreshing ? "size-3 animate-spin" : "size-3"} />
              {refreshing ? "Updating" : "Live"}
            </Badge>
            <TrustLine />
          </div>
        </header>

        {sessions.isError ? (
          <div className="mb-6 rounded-lg border border-destructive/30 bg-destructive/5 p-4 sm:p-5">
            <p className="font-medium text-destructive">Case tracker could not load</p>
            <p className="mt-1 text-sm leading-6 text-destructive/90">
              {friendlyErrorMessage(
                sessions.error,
                "Sessions could not be loaded. Confirm the HakiScribe service is running, then refresh.",
              )}
            </p>
            <Button type="button" variant="outline" size="sm" className="mt-4" onClick={() => void sessions.refetch()}>
              <RefreshCw className="size-3.5" />
              Try again
            </Button>
          </div>
        ) : null}

        <section className="mb-9 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard icon={<Scale className="size-4" />} label="Sessions" value={loaded.length} />
          <StatCard icon={<Flag className="size-4" />} label="Flagged moments" value={flagCount} />
          <StatCard icon={<FileText className="size-4" />} label="Documents" value={documents.length} />
          <StatCard icon={<CalendarClock className="size-4" />} label="Upcoming dates" value={upcoming.length} />
        </section>

        <Tabs defaultValue="sessions">
          <TabsList className="mb-5 w-full justify-start overflow-x-auto">
            <TabsTrigger value="sessions">Sessions</TabsTrigger>
            <TabsTrigger value="documents">Documents ({documents.length})</TabsTrigger>
            <TabsTrigger value="diary">Diary ({upcoming.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="documents">
            <SectionHeading eyebrow="Artifacts" title="Generated documents" />
            {documents.length === 0 ? (
              <p className="rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
                No documents have been generated yet. Draft one from a session's action tray.
              </p>
            ) : (
              <ul className="grid gap-3">
                {documents.map((document, index) => (
                  <li
                    key={`${document.sessionId}-${index}`}
                    className="grid gap-2 rounded-lg border border-border bg-card p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start sm:gap-4"
                  >
                    <div className="min-w-0">
                      <p className="font-serif text-base font-semibold capitalize">{document.kind}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {formatDate(document.createdAt)} · From {document.sessionTitle}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <Badge variant={document.url ? "outline" : "secondary"} className="text-[11px]">
                          {document.url ? "In Ambiguous" : "Saved on the record"}
                        </Badge>
                        {document.archived ? (
                          <Badge variant="secondary" className="text-[11px]">
                            Archived copy
                          </Badge>
                        ) : null}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {document.url ? (
                        <Button asChild size="sm" variant="outline">
                          <a href={document.url} target="_blank" rel="noreferrer">
                            Open in Ambiguous <ExternalLink className="ml-1 size-3" />
                          </a>
                        </Button>
                      ) : null}
                      <Button asChild size="sm" variant="ghost">
                        <Link
                          to="/sessions/$sessionId"
                          params={{ sessionId: document.sessionId }}
                          search={{ fresh: false }}
                        >
                          Open session
                        </Link>
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>

          <TabsContent value="diary">
          <section className="mb-10">
          <SectionHeading eyebrow="Diary" title="Upcoming calendar events" />
          {upcoming.length === 0 ? (
            <p className="rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
              No future dates have been generated yet. Generate a calendar event from a session to see it here.
            </p>
          ) : (
            <ul className="grid gap-3">
              {upcoming.map((event, index) => (
                <li
                  key={`${event.sessionId}-${index}`}
                  className="grid gap-2 rounded-lg border border-border bg-card p-4 sm:grid-cols-[10rem_minmax(0,1fr)] sm:items-start sm:gap-4"
                >
                  <p className="text-sm font-semibold text-primary">{formatDate(event.start)}</p>
                  <div className="min-w-0">
                    <p className="font-medium">{event.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {event.location ? `${event.location} · ` : ""}
                      From {event.sessionTitle}
                    </p>
                    {event.attendees.length > 0 ? (
                      <p className="mt-1 text-xs text-muted-foreground">With {event.attendees.join(", ")}</p>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
          </section>
          </TabsContent>

          <TabsContent value="sessions">
          <section>
          <SectionHeading eyebrow="Record" title="All sessions" />
          {loaded.length === 0 && !sessions.isLoading ? (
            <p className="rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
              No sessions yet.
            </p>
          ) : null}
          <ul className="grid gap-4">
            {loaded.map((detail) => {
              const sessionDocuments = documents.filter((item) => item.sessionId === detail.id);
              const sessionEvents = events.filter((item) => item.sessionId === detail.id);
              return (
                <li key={detail.id} className="rounded-lg border border-border bg-card p-4 sm:p-5">
                  <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
                    <div className="min-w-0">
                      <Link
                        to="/sessions/$sessionId"
                        params={{ sessionId: detail.id }}
                        search={{ fresh: false }}
                        className="font-serif text-lg font-semibold underline-offset-4 hover:underline"
                      >
                        {detail.title}
                      </Link>
                      <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <SourceIcon source={detail.source} className="size-3.5" />
                        {formatDay(detail.created_at)}
                        {detail.matters && detail.matters.length > 0
                          ? ` · ${detail.matters.map((matter) => matter.matter_name).join(", ")}`
                          : ""}
                      </p>
                    </div>
                    <StatusBadge status={detail.status} />
                  </div>

                  <div className="mt-4 grid gap-4 sm:grid-cols-3">
                    <TrackerColumn title="Flagged moments" icon={<Flag className="size-3.5" />}>
                      {detail.flagged_moments.length === 0 ? (
                        <p className="text-xs text-muted-foreground">None flagged.</p>
                      ) : (
                        <ul className="grid gap-1 text-xs">
                          {detail.flagged_moments.map((flag) => (
                            <li key={flag.id} className="truncate">
                              {flag.label ?? "Flagged moment"}
                              <span className="text-muted-foreground">
                                {" "}
                                · {Math.floor(flag.at_ms / 60000)}m{String(Math.floor((flag.at_ms % 60000) / 1000)).padStart(2, "0")}s
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </TrackerColumn>

                    <TrackerColumn title="Generated documents" icon={<FileText className="size-3.5" />}>
                      {sessionDocuments.length === 0 ? (
                        <p className="text-xs text-muted-foreground">Nothing drafted yet.</p>
                      ) : (
                        <ul className="grid gap-1 text-xs">
                          {sessionDocuments.map((document, index) => (
                            <li key={`${document.kind}-${index}`} className="min-w-0">
                              <span className="capitalize">{document.kind}</span>
                              {document.url ? (
                                <a
                                  href={document.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="ml-2 inline-flex items-center gap-1 text-primary underline"
                                >
                                  Open <ExternalLink className="size-3" />
                                </a>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      )}
                    </TrackerColumn>

                    <TrackerColumn title="Dates set" icon={<CalendarClock className="size-3.5" />}>
                      {sessionEvents.length === 0 ? (
                        <p className="text-xs text-muted-foreground">No dates set.</p>
                      ) : (
                        <ul className="grid gap-1 text-xs">
                          {sessionEvents.map((event, index) => (
                            <li key={`${event.title}-${index}`} className="min-w-0">
                              <span className="block truncate font-medium">{event.title}</span>
                              <span className="text-muted-foreground">{formatDate(event.start)}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </TrackerColumn>
                  </div>

                  <div className="mt-4">
                    <Button asChild variant="outline" size="sm">
                      <Link to="/sessions/$sessionId" params={{ sessionId: detail.id }} search={{ fresh: false }}>
                        Open session
                      </Link>
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
          </section>
          </TabsContent>
        </Tabs>
      </main>
      <WorkspaceFooter />
    </PageShell>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        {icon}
        <span className="truncate">{label}</span>
      </p>
      <p className="mt-2 font-serif text-2xl font-semibold">{value}</p>
    </div>
  );
}

function TrackerColumn({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="min-w-0 rounded-md border border-border/70 bg-muted/30 p-3">
      <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        {icon}
        <span className="truncate">{title}</span>
      </p>
      {children}
    </div>
  );
}
