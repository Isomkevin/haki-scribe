import { useState } from "react";
import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { CalendarClock, ExternalLink, FileText, Flag, Gavel, RefreshCw, Scale } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useDemoMode } from "@/hooks/use-demo-mode";
import { filterDemoSessions } from "@/lib/demo-mode";
import {
  hakiApi,
  friendlyErrorMessage,
  type ActionResult,
  type HearingMatchCandidate,
  type HearingRecord,
  type SessionDetail,
} from "@/lib/hakiscribe";
import { PageShell, SectionHeading, SourceIcon, StatusBadge, WorkspaceFooter } from "./shell";
import { TrustLine } from "./brand";
import { ContactDirectory } from "./contacts";

const REFRESH_MS = 20_000;

export interface TrackedDocument {
  sessionId: string;
  sessionTitle: string;
  kind: string;
  url: string | null;
  createdAt: string | null;
  archived: boolean;
}

export interface TrackedEvent {
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

export function documentOf(result: ActionResult, detail: SessionDetail): TrackedDocument | null {
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

export function eventOf(result: ActionResult, detail: SessionDetail): TrackedEvent | null {
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

export function formatDate(value: string | null) {
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

export function formatDay(value: string) {
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

        <HearingsPanel />

        <Tabs defaultValue="sessions">
          <TabsList className="mb-5 w-full justify-start overflow-x-auto">
            <TabsTrigger value="sessions">Sessions</TabsTrigger>
            <TabsTrigger value="documents">Documents ({documents.length})</TabsTrigger>
            <TabsTrigger value="diary">Diary ({upcoming.length})</TabsTrigger>
            <TabsTrigger value="contacts">Contacts</TabsTrigger>
          </TabsList>

          <TabsContent value="contacts">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
              <SectionHeading eyebrow="People" title="Contacts across matters" />
              <Button asChild variant="outline" size="sm">
                <Link to="/contacts">Open contacts directory</Link>
              </Button>
            </div>
            <ContactDirectory />
          </TabsContent>

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

function HearingsPanel() {
  const queryClient = useQueryClient();
  const pending = useQuery({
    queryKey: ["hearings-pending"],
    queryFn: hakiApi.listPendingHearings,
    retry: false,
  });
  const [title, setTitle] = useState("");
  const [caseRef, setCaseRef] = useState("");
  const [candidates, setCandidates] = useState<Record<string, HearingMatchCandidate[]>>({});
  const [busy, setBusy] = useState(false);

  async function importManual() {
    if (!title.trim()) {
      toast.error("Enter a hearing title");
      return;
    }
    setBusy(true);
    try {
      const result = await hakiApi.importManualHearing({
        title: title.trim(),
        case_reference: caseRef.trim() || undefined,
      });
      setCandidates((prev) => ({ ...prev, [result.hearing.id]: result.candidates }));
      setTitle("");
      setCaseRef("");
      await queryClient.invalidateQueries({ queryKey: ["hearings-pending"] });
      toast.success("Hearing imported — confirm a matter match before opening a session");
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Could not import hearing."));
    } finally {
      setBusy(false);
    }
  }

  async function importCalendar() {
    setBusy(true);
    try {
      const result = await hakiApi.importCalendarHearings();
      toast.success(`Imported ${result.imported} calendar hearing(s)`);
      await queryClient.invalidateQueries({ queryKey: ["hearings-pending"] });
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Calendar import failed. Connect Google Calendar first."));
    } finally {
      setBusy(false);
    }
  }

  async function confirm(hearing: HearingRecord, matterId: string) {
    setBusy(true);
    try {
      await hakiApi.confirmHearing(hearing.id, { decision: "confirm", matter_id: matterId });
      const created = await hakiApi.createHearingSession(hearing.id);
      await queryClient.invalidateQueries({ queryKey: ["hearings-pending"] });
      toast.success("Matter confirmed — session ready");
      window.location.assign(`/sessions/${created.session.id}`);
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Could not confirm hearing."));
    } finally {
      setBusy(false);
    }
  }

  async function loadMatches(hearingId: string) {
    try {
      const result = await hakiApi.matchHearing(hearingId);
      setCandidates((prev) => ({ ...prev, [hearingId]: result.candidates }));
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Could not propose matches."));
    }
  }

  const rows = pending.data ?? [];

  return (
    <section className="mb-9 rounded-lg border border-border bg-card p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
            <Gavel className="size-3.5" />
            Virtual hearings
          </p>
          <h2 className="mt-1 font-serif text-xl font-semibold">Matter match confirmation</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Ambiguous matches never attach silently. Confirm the HakiChain matter, then open a session.
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => void importCalendar()}>
          Import Google Calendar
        </Button>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Input
          className="max-w-xs"
          placeholder="Hearing title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <Input
          className="max-w-[12rem]"
          placeholder="Case / matter ref"
          value={caseRef}
          onChange={(e) => setCaseRef(e.target.value)}
        />
        <Button type="button" size="sm" disabled={busy} onClick={() => void importManual()}>
          Add manual hearing
        </Button>
      </div>

      {pending.isError ? (
        <p className="mt-4 text-sm text-muted-foreground">
          Hearings API unavailable — start the backend to use virtual court matching.
        </p>
      ) : rows.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">No hearings awaiting confirmation.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {rows.map((hearing) => {
            const cands = candidates[hearing.id] ?? [];
            return (
              <li key={hearing.id} className="rounded-md border border-border/80 bg-muted/20 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium">{hearing.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {hearing.source} · {hearing.status}
                      {hearing.case_reference ? ` · ${hearing.case_reference}` : ""}
                      {hearing.match_confidence != null ? ` · confidence ${(hearing.match_confidence * 100).toFixed(0)}%` : ""}
                    </p>
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={() => void loadMatches(hearing.id)}>
                    Propose matches
                  </Button>
                </div>
                {cands.length > 0 && (
                  <ul className="mt-3 space-y-2">
                    {cands.map((c) => (
                      <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                        <span>
                          Matter {c.matter_id.slice(0, 8)}… · score {(c.score * 100).toFixed(0)}%
                          {c.rationale ? ` — ${c.rationale}` : ""}
                        </span>
                        <Button type="button" size="sm" disabled={busy} onClick={() => void confirm(hearing, c.matter_id)}>
                          Confirm & open
                        </Button>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
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
