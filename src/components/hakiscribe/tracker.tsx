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
  type HearingProceedings,
  type HearingRecord,
  type ProceedingsItem,
  type SessionDetail,
} from "@/lib/hakiscribe";
import { PageShell, SectionHeading, SourceIcon, StatusBadge, WorkspaceFooter } from "./shell";
import { TrustLine } from "./brand";
import { ContactDirectory } from "./contacts";

const REFRESH_MS = 20_000;
const PIPELINE_POLL_MS = 3_000;
// CPU transcription of a long hearing can take a while; stop polling after this.
const PIPELINE_POLL_LIMIT_MS = 3 * 60 * 60 * 1000;

type PipelineState = { state?: string; step?: string; error?: string | null };

function pipelineOf(hearing: HearingRecord): PipelineState | null {
  const pipeline = hearing.platform_metadata?.["pipeline"];
  return pipeline && typeof pipeline === "object" ? (pipeline as PipelineState) : null;
}

function isAmbiguousMatch(hearing: HearingRecord): boolean {
  const match = hearing.platform_metadata?.["match"];
  return Boolean(
    match && typeof match === "object" && (match as { ambiguous?: boolean }).ambiguous,
  );
}

async function waitForPipeline(hearingId: string): Promise<HearingProceedings> {
  const deadline = Date.now() + PIPELINE_POLL_LIMIT_MS;
  for (;;) {
    const proc = await hakiApi.getHearingProceedings(hearingId);
    const state = proc.pipeline?.state;
    if (state !== "queued" && state !== "running") return proc;
    if (Date.now() > deadline) throw new Error("Processing is still running — check back later.");
    await new Promise((resolve) => setTimeout(resolve, PIPELINE_POLL_MS));
  }
}

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
  const hearings = useQuery({
    queryKey: ["hearings"],
    queryFn: hakiApi.listHearings,
    retry: false,
    refetchInterval: REFRESH_MS,
  });
  const matters = useQuery({ queryKey: ["matters"], queryFn: hakiApi.listMatters, retry: false });
  const matterName = (id: string) => {
    const m = matters.data?.find((row) => row.id === id);
    return m ? `${m.client_name} — ${m.matter_name}` : `Matter ${id.slice(0, 8)}…`;
  };
  const matterLinked = (id: string | null | undefined) => {
    if (!id) return null;
    return matters.data?.find((row) => row.id === id) ?? null;
  };
  const [languageHint, setLanguageHint] = useState("");
  const [title, setTitle] = useState("");
  const [caseRef, setCaseRef] = useState("");
  const [candidates, setCandidates] = useState<Record<string, HearingMatchCandidate[]>>({});
  const [proceedings, setProceedings] = useState<Record<string, HearingProceedings>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [hcMatters, setHcMatters] = useState<
    { workspace_id: string; client_id: string; name: string; client: string; role?: string }[]
  >([]);
  const [hcPickerMatterId, setHcPickerMatterId] = useState<string>("");
  const [hcPickerWorkspaceId, setHcPickerWorkspaceId] = useState<string>("");
  const [hcBusy, setHcBusy] = useState(false);

  async function refreshHearings() {
    await queryClient.invalidateQueries({ queryKey: ["hearings"] });
    await queryClient.invalidateQueries({ queryKey: ["hearings-pending"] });
    // Confirming or processing a hearing creates/fills its session in the list below.
    await queryClient.invalidateQueries({ queryKey: ["sessions"] });
  }

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
      await refreshHearings();
      toast.success("Hearing imported — confirm a matter match before processing");
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Could not import hearing."));
    } finally {
      setBusy(false);
    }
  }

  async function importFrom(source: "calendar" | "teams" | "zoom") {
    setBusy(true);
    try {
      const result =
        source === "calendar"
          ? await hakiApi.importCalendarHearings()
          : source === "teams"
            ? await hakiApi.importTeamsHearings()
            : await hakiApi.importZoomHearings();
      toast.success(`Imported ${result.imported} ${source} hearing(s)`);
      await refreshHearings();
    } catch (error) {
      toast.error(friendlyErrorMessage(error, `${source} import failed. Connect the connector first.`));
    } finally {
      setBusy(false);
    }
  }

  async function confirm(hearing: HearingRecord, matterId: string) {
    setBusyId(hearing.id);
    try {
      await hakiApi.confirmHearing(hearing.id, { decision: "confirm", matter_id: matterId });
      const created = await hakiApi.createHearingSession(hearing.id);
      await refreshHearings();
      toast.success("Matter confirmed — session linked. Upload or fetch the recording next.");
      // Keep the user on tracker for ingest/process; session is available via link.
      void created;
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Could not confirm hearing."));
    } finally {
      setBusyId(null);
    }
  }

  async function reject(hearing: HearingRecord) {
    setBusyId(hearing.id);
    try {
      await hakiApi.confirmHearing(hearing.id, { decision: "reject" });
      setCandidates((prev) => ({ ...prev, [hearing.id]: [] }));
      await refreshHearings();
      toast.success("Match rejected — no matter linked");
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Could not reject match."));
    } finally {
      setBusyId(null);
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

  async function onUpload(hearing: HearingRecord, file: File, kind: "recording" | "transcript") {
    setBusyId(hearing.id);
    try {
      await hakiApi.uploadHearingFile(hearing.id, file, file.name, kind);
      await refreshHearings();
      toast.success(kind === "transcript" ? "Transcript attached" : "Recording attached");
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Upload failed."));
    } finally {
      setBusyId(null);
    }
  }

  async function onFetch(hearing: HearingRecord, prefer: "audio" | "transcript") {
    setBusyId(hearing.id);
    try {
      await hakiApi.fetchHearingRecording(hearing.id, prefer);
      await refreshHearings();
      toast.success(prefer === "transcript" ? "Platform transcript fetched" : "Platform recording fetched");
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Platform fetch failed."));
    } finally {
      setBusyId(null);
    }
  }

  async function onProcess(hearing: HearingRecord) {
    setBusyId(hearing.id);
    try {
      // Queue server-side and poll: long recordings outlive a single HTTP request.
      await hakiApi.processHearing(hearing.id, {
        wait: false,
        ...(languageHint ? { languageHint } : {}),
      });
      await refreshHearings();
      const proc = await waitForPipeline(hearing.id);
      setProceedings((prev) => ({ ...prev, [hearing.id]: proc }));
      await refreshHearings();
      if (proc.pipeline?.state === "error") {
        toast.error(`Processing failed: ${proc.pipeline.error ?? "unknown error"}`);
      } else {
        toast.success("Hearing processed — review the extracted record");
      }
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Processing failed."));
    } finally {
      setBusyId(null);
    }
  }

  async function onLoadProceedings(hearingId: string) {
    try {
      const proc = await hakiApi.getHearingProceedings(hearingId);
      setProceedings((prev) => ({ ...prev, [hearingId]: proc }));
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Could not load proceedings."));
    }
  }

  async function onReview(hearing: HearingRecord) {
    setBusyId(hearing.id);
    try {
      await hakiApi.reviewHearing(hearing.id);
      await refreshHearings();
      toast.success("Hearing marked reviewed");
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Review failed — process the hearing first."));
    } finally {
      setBusyId(null);
    }
  }

  async function loadHakiChainMatters() {
    setHcBusy(true);
    try {
      const result = await hakiApi.listHakiChainMatters();
      setHcMatters(result.matters ?? []);
      if ((result.matters ?? []).length === 0) {
        toast.message("No HakiChain matters returned for this token");
      } else {
        toast.success(`Loaded ${result.matters.length} HakiChain matter(s)`);
      }
    } catch (error) {
      toast.error(
        friendlyErrorMessage(
          error,
          "Could not list HakiChain matters — connect a hkc_ token under Settings → Connectors.",
        ),
      );
    } finally {
      setHcBusy(false);
    }
  }

  async function linkSelectedHakiChainMatter() {
    if (!hcPickerMatterId || !hcPickerWorkspaceId) {
      toast.error("Pick a local matter and a HakiChain workspace");
      return;
    }
    setHcBusy(true);
    try {
      const result = await hakiApi.linkHakiChainMatter({
        scribe_matter_id: hcPickerMatterId,
        workspace_id: hcPickerWorkspaceId,
      });
      await queryClient.invalidateQueries({ queryKey: ["matters"] });
      toast.success(
        result.workspace_url
          ? "Linked to HakiChain WorkSpace — File to HakiChain will use this matter"
          : "Linked to HakiChain matter",
      );
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Could not link HakiChain matter."));
    } finally {
      setHcBusy(false);
    }
  }

  async function onFileToHakiChain(hearing: HearingRecord) {
    setBusyId(hearing.id);
    try {
      const result = await hakiApi.fileHearingToHakiChain(hearing.id);
      await refreshHearings();
      toast.success(
        result.workspace_url
          ? "Filed to HakiChain WorkSpace — use Open WorkSpace on the hearing row"
          : "Hearing pack filed to HakiChain",
      );
    } catch (error) {
      toast.error(
        friendlyErrorMessage(
          error,
          "Filing failed — mark reviewed and connect HakiChain under Settings → Connectors.",
        ),
      );
    } finally {
      setBusyId(null);
    }
  }

  async function onStartCapture(hearing: HearingRecord) {
    setBusyId(hearing.id);
    try {
      await hakiApi.startHearingCapture(hearing.id);
      await refreshHearings();
      toast.success("Capture started — bot joining when SDK credentials are configured");
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Could not start live capture."));
    } finally {
      setBusyId(null);
    }
  }

  async function onStopCapture(hearing: HearingRecord) {
    setBusyId(hearing.id);
    try {
      await hakiApi.stopHearingCapture(hearing.id);
      await refreshHearings();
      toast.success("Capture stopped");
    } catch (error) {
      toast.error(friendlyErrorMessage(error, "Could not stop capture."));
    } finally {
      setBusyId(null);
    }
  }

  const rows = hearings.data ?? [];
  const pendingCount = rows.filter((h) => h.status === "pending_confirm" || h.status === "scheduled").length;

  return (
    <section className="mb-9 rounded-lg border border-border bg-card p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
            <Gavel className="size-3.5" />
            Virtual hearings
          </p>
          <h2 className="mt-1 font-serif text-xl font-semibold">            Match → ingest → process → review → File to HakiChain</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Connected to Stage B pipeline. Matter matches never attach silently. AI summaries are not court orders —
            grounded items cite transcript quotes; ungrounded items are flagged. Link a HakiChain WorkSpace so filing
            does not invent a disconnected matter.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => void importFrom("calendar")}>
            Google Calendar
          </Button>
          <Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => void importFrom("teams")}>
            Teams
          </Button>
          <Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => void importFrom("zoom")}>
            Zoom
          </Button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Input
          className="max-w-xs"
          placeholder="Hearing title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <Input
          className="max-w-48"
          placeholder="Case / matter ref"
          value={caseRef}
          onChange={(e) => setCaseRef(e.target.value)}
        />
        <Button type="button" size="sm" disabled={busy} onClick={() => void importManual()}>
          Add manual hearing
        </Button>
      </div>

      <div className="mt-3 rounded-md border border-dashed border-border/80 bg-muted/10 p-3">
        <p className="text-xs font-medium text-muted-foreground">Link local matter → HakiChain WorkSpace</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" disabled={hcBusy} onClick={() => void loadHakiChainMatters()}>
            {hcBusy ? "Loading…" : "Load HakiChain matters"}
          </Button>
          <select
            aria-label="Local matter to link"
            className="h-9 max-w-xs rounded-md border border-input bg-background px-2 text-sm"
            value={hcPickerMatterId}
            onChange={(e) => setHcPickerMatterId(e.target.value)}
          >
            <option value="">Local matter…</option>
            {(matters.data ?? []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.client_name} — {m.matter_name}
                {m.hakichain_workspace_id ? " (linked)" : ""}
              </option>
            ))}
          </select>
          <select
            aria-label="HakiChain workspace"
            className="h-9 max-w-xs rounded-md border border-input bg-background px-2 text-sm"
            value={hcPickerWorkspaceId}
            onChange={(e) => setHcPickerWorkspaceId(e.target.value)}
          >
            <option value="">HakiChain workspace…</option>
            {hcMatters.map((m) => (
              <option key={m.workspace_id} value={m.workspace_id}>
                {m.client} — {m.name}
                {m.role ? ` (${m.role})` : ""}
              </option>
            ))}
          </select>
          <Button
            type="button"
            size="sm"
            disabled={hcBusy || !hcPickerMatterId || !hcPickerWorkspaceId}
            onClick={() => void linkSelectedHakiChainMatter()}
          >
            Link WorkSpace
          </Button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <select
          aria-label="Hearing language"
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={languageHint}
          onChange={(e) => setLanguageHint(e.target.value)}
        >
          <option value="">Language: auto</option>
          <option value="en">English</option>
          <option value="sw">Kiswahili</option>
        </select>
      </div>

      {hearings.isError ? (
        <p className="mt-4 text-sm text-muted-foreground">
          Hearings API unavailable — start the backend to use virtual court matching.
        </p>
      ) : rows.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">
          No hearings yet. Import from Calendar/Teams/Zoom or add a manual hearing.
        </p>
      ) : (
        <>
          <p className="mt-4 text-xs text-muted-foreground">
            {rows.length} hearing(s) · {pendingCount} awaiting match confirmation
          </p>
          <ul className="mt-3 space-y-3">
            {rows.map((hearing) => {
              const cands = candidates[hearing.id] ?? [];
              const proc = proceedings[hearing.id];
              const rowBusy = busyId === hearing.id;
              const canIngest = Boolean(hearing.matter_id) && !["transcribed", "reviewed", "filed", "rejected"].includes(hearing.status);
              const pipeline = pipelineOf(hearing);
              const pipelineActive = pipeline?.state === "queued" || pipeline?.state === "running";
              // Backend requires a confirmed matter and a stored recording/transcript.
              const canProcess =
                Boolean(hearing.matter_id) &&
                Boolean(hearing.recording_object_key) &&
                ["ingested", "transcribed"].includes(hearing.status) &&
                !pipelineActive;
              const canReview = hearing.status === "transcribed";
              const canFile =
                Boolean(hearing.matter_id) &&
                Boolean(hearing.session_id) &&
                (hearing.status === "reviewed" || hearing.status === "filed");
              const filingMeta = (hearing.platform_metadata?.hakichain_filing ?? null) as
                | { workspace_url?: string; ok?: boolean; filed_at?: string }
                | null;
              const platformFetch = hearing.source === "zoom" || hearing.source === "teams_graph";
              const canLiveCapture =
                Boolean(hearing.matter_id) &&
                platformFetch &&
                (hearing.status === "matched" || hearing.status === "capturing");
              const captureActive = hearing.status === "capturing";
              const linkedMatter = matterLinked(hearing.matter_id);

              return (
                <li key={hearing.id} className="rounded-md border border-border/80 bg-muted/20 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-medium">{hearing.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {hearing.source} · {hearing.status}
                        {hearing.case_reference ? ` · ${hearing.case_reference}` : ""}
                        {hearing.match_confidence != null
                          ? ` · confidence ${(hearing.match_confidence * 100).toFixed(0)}%`
                          : ""}
                        {hearing.recording_object_key ? " · recording on file" : ""}
                        {linkedMatter?.hakichain_workspace_id ? " · HakiChain linked" : ""}
                      </p>
                      {pipeline?.state && (
                        <p
                          className={
                            pipeline.state === "error"
                              ? "mt-0.5 text-xs text-destructive"
                              : "mt-0.5 text-xs text-muted-foreground"
                          }
                        >
                          Processing: {pipeline.state}
                          {pipeline.step && pipeline.state !== "error" ? ` / ${pipeline.step}` : ""}
                          {pipeline.error ? ` — ${pipeline.error}` : ""}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(hearing.status === "scheduled" || hearing.status === "pending_confirm") && (
                        <Button type="button" variant="outline" size="sm" onClick={() => void loadMatches(hearing.id)}>
                          Propose matches
                        </Button>
                      )}
                      {hearing.session_id && (
                        <Button asChild variant="outline" size="sm">
                          <Link to="/sessions/$sessionId" params={{ sessionId: hearing.session_id }} search={{ fresh: false }}>
                            Open session
                          </Link>
                        </Button>
                      )}
                    </div>
                  </div>

                  {hearing.status === "pending_confirm" && isAmbiguousMatch(hearing) && (
                    <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                      Top matches are too close to call — check the case number before confirming.
                    </p>
                  )}
                  {cands.length > 0 && (hearing.status === "scheduled" || hearing.status === "pending_confirm") && (
                    <ul className="mt-3 space-y-2">
                      {cands.map((c) => (
                        <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                          <span>
                            {matterName(c.matter_id)} · score {(c.score * 100).toFixed(0)}%
                            {c.rationale ? ` — ${c.rationale}` : ""}
                          </span>
                          <Button
                            type="button"
                            size="sm"
                            disabled={rowBusy}
                            onClick={() => void confirm(hearing, c.matter_id)}
                          >
                            Confirm matter
                          </Button>
                        </li>
                      ))}
                      <li>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={rowBusy}
                          onClick={() => void reject(hearing)}
                        >
                          None of these — reject
                        </Button>
                      </li>
                    </ul>
                  )}

                  {canIngest && (
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <label className="inline-flex cursor-pointer items-center gap-2 text-xs">
                        <span className="rounded-md border border-border bg-background px-2 py-1.5 font-medium">
                          Upload recording
                        </span>
                        <input
                          type="file"
                          accept="audio/*,video/*,.webm,.wav,.mp3,.mp4,.m4a"
                          className="sr-only"
                          disabled={rowBusy}
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) void onUpload(hearing, file, "recording");
                            e.target.value = "";
                          }}
                        />
                      </label>
                      <label className="inline-flex cursor-pointer items-center gap-2 text-xs">
                        <span className="rounded-md border border-border bg-background px-2 py-1.5 font-medium">
                          Upload VTT
                        </span>
                        <input
                          type="file"
                          accept=".vtt,text/vtt,text/plain"
                          className="sr-only"
                          disabled={rowBusy}
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) void onUpload(hearing, file, "transcript");
                            e.target.value = "";
                          }}
                        />
                      </label>
                      {platformFetch && (
                        <>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={rowBusy}
                            onClick={() => void onFetch(hearing, "audio")}
                          >
                            Fetch recording
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={rowBusy}
                            onClick={() => void onFetch(hearing, "transcript")}
                          >
                            Fetch transcript
                          </Button>
                        </>
                      )}
                      {canLiveCapture && !captureActive && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={rowBusy}
                          onClick={() => void onStartCapture(hearing)}
                        >
                          Start capture
                        </Button>
                      )}
                      {captureActive && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={rowBusy}
                          onClick={() => void onStopCapture(hearing)}
                        >
                          Stop capture
                        </Button>
                      )}
                    </div>
                  )}

                  <div className="mt-3 flex flex-wrap gap-2">
                    {canProcess && (
                      <Button type="button" size="sm" disabled={rowBusy} onClick={() => void onProcess(hearing)}>
                        {rowBusy ? "Processing…" : hearing.status === "transcribed" ? "Re-process" : "Process hearing"}
                      </Button>
                    )}
                    {(hearing.status === "transcribed" || hearing.status === "reviewed" || hearing.status === "ingested") && (
                      <Button type="button" variant="outline" size="sm" onClick={() => void onLoadProceedings(hearing.id)}>
                        Show proceedings
                      </Button>
                    )}
                    {canReview && (
                      <Button type="button" size="sm" disabled={rowBusy} onClick={() => void onReview(hearing)}>
                        Mark reviewed
                      </Button>
                    )}
                    {canFile && (
                      <Button
                        type="button"
                        size="sm"
                        variant={hearing.status === "filed" ? "outline" : "default"}
                        disabled={rowBusy}
                        onClick={() => void onFileToHakiChain(hearing)}
                      >
                        {rowBusy
                          ? "Filing…"
                          : hearing.status === "filed"
                            ? "Re-file to HakiChain"
                            : "File to HakiChain"}
                      </Button>
                    )}
                    {filingMeta?.workspace_url && (
                      <Button type="button" variant="ghost" size="sm" asChild>
                        <a href={filingMeta.workspace_url} target="_blank" rel="noopener noreferrer">
                          Open WorkSpace
                        </a>
                      </Button>
                    )}
                  </div>

                  {proc?.proceedings && <ProceedingsView proceedings={proc} />}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}

function ProceedingsView({ proceedings }: { proceedings: HearingProceedings }) {
  const rules = proceedings.proceedings?.rules ?? [];
  const llmItems = proceedings.proceedings?.llm?.items ?? [];
  const ungrounded = proceedings.proceedings?.llm?.ungrounded ?? [];
  const grounded = [...rules, ...llmItems];

  return (
    <div className="mt-3 rounded-md border border-border/60 bg-background/80 p-3 text-sm">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        Proceedings intelligence
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Pipeline: {proceedings.pipeline?.state ?? "—"}
        {proceedings.pipeline?.step ? ` / ${proceedings.pipeline.step}` : ""}
        {proceedings.proceedings?.llm?.status ? ` · LLM ${proceedings.proceedings.llm.status}` : ""}
      </p>
      {grounded.length === 0 && ungrounded.length === 0 ? (
        <p className="mt-2 text-xs text-muted-foreground">No extracted items yet.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {grounded.map((item, idx) => (
            <ProceedingsRow key={`g-${idx}`} item={item} flagged={false} />
          ))}
          {ungrounded.map((item, idx) => (
            <ProceedingsRow key={`u-${idx}`} item={item} flagged />
          ))}
        </ul>
      )}
      <p className="mt-2 text-[11px] text-muted-foreground">
        AI-generated items are not authenticated court orders. Prefer quote-grounded rows.
      </p>
    </div>
  );
}

function ProceedingsRow({ item, flagged }: { item: ProceedingsItem; flagged: boolean }) {
  const label = item.text || item.purpose || item.name || item.kind;
  const jump =
    item.segment_id && item.start_ms != null
      ? `seg ${item.segment_id.slice(0, 8)}… @ ${Math.round(item.start_ms / 1000)}s`
      : null;
  return (
    <li className={flagged ? "rounded border border-amber-500/40 bg-amber-500/5 p-2" : "rounded border border-border/50 p-2"}>
      <p className="font-medium">
        {item.kind}
        {flagged ? " · ungrounded" : ""} · {item.method}
      </p>
      <p className="mt-0.5 text-xs text-muted-foreground">{label}</p>
      {item.quote ? <p className="mt-1 text-xs italic text-foreground/80">“{item.quote}”</p> : null}
      {jump ? <p className="mt-1 text-[11px] text-muted-foreground">{jump}</p> : null}
      {item.reason ? <p className="mt-1 text-[11px] text-amber-700 dark:text-amber-400">{item.reason}</p> : null}
    </li>
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
