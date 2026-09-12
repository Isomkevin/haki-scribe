import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  BriefcaseBusiness,
  CalendarDays,
  Check,
  ChevronDown,
  Clock3,
  ContactRound,
  Copy,
  Download,
  FileText,
  Flag,
  Globe,
  Headphones,
  Newspaper,
  LockKeyhole,
  MessageCircle,
  Mic,
  NotebookPen,
  Radio,
  RefreshCw,
  Scale,
  Sparkles,
  Square,
  UnlockKeyhole,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ComponentType } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  type ActionResult,
  type ActionType,
  type Contact,
  type DetectedAction,
  type FlaggedMoment,
  type Matter,
  type NewsHit,
  type ResearchSource,
  type Session,
  type SessionDetail,
  type SessionSource,
  type TranscriptSegment,
  displayValue,
  downloadTextFile,
  formatDuration,
  hakiApi,
  hasApiConfiguration,
  omiWebhookUrl,
  whatsappShareUrl,
  websocketUrl,
} from "@/lib/hakiscribe";
import { TrustLine } from "./brand";
import {
  FlowProgress,
  PageShell,
  SectionEyebrow,
  SectionHeading,
  SourceIcon,
  StatusBadge,
  WorkspaceFooter,
} from "./shell";

const actionIcons: Record<ActionType, ComponentType<{ className?: string }>> = {
  draft_document: FileText,
  calendar_event: CalendarDays,
  workspace_matter: BriefcaseBusiness,
  crm_entry: ContactRound,
  private_note: NotebookPen,
  time_entry: Clock3,
  legal_research: Scale,
  web_search: Globe,
  llm_task: Sparkles,
};

const flagLabels = ["Date", "Admission", "Contract term", "Hearing"];
const hiddenFieldKeys = new Set(["detection_mode", "background_info"]);

const practiceSteps = [
  { n: "01", title: "Listen first", copy: "Mic or Omi. Flag what matters without looking down." },
  { n: "02", title: "Verify the record", copy: "Name speakers. Lock privileged lines before any model sees them." },
  { n: "03", title: "Choose the work", copy: "Letters, dates, matters, contacts, notes, and time — each sourced." },
];

const environments = [
  { place: "In the room", title: "Mic or Omi wearable", copy: "The agent listens where the conversation happens. Flag a date or admission without breaking eye contact." },
  { place: "In the pocket", title: "WhatsApp handoff", copy: "Kenyan practice already lives in WhatsApp. Share an editable draft for review — never auto-sent as legal advice." },
  { place: "At the desk", title: "Docs, calendar, CRM", copy: "Chosen work lands in Ambiguous and the HakiChain library: a letter, a hearing, a matter, a billable hour." },
];

function ConnectionError({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <Alert variant="destructive" className="border-destructive/30 bg-card">
      <AlertCircle />
      <AlertTitle>Connection unavailable</AlertTitle>
      <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
        <span>{message}</span>
        {retry && <Button variant="outline" size="sm" onClick={retry}><RefreshCw /> Try again</Button>}
      </AlertDescription>
    </Alert>
  );
}

export function HomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [source, setSource] = useState<SessionSource>("mic");
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("code-switch");
  const sessions = useQuery({
    queryKey: ["sessions"],
    queryFn: hakiApi.listSessions,
    enabled: hasApiConfiguration,
    retry: false,
  });
  const matters = useQuery({
    queryKey: ["matters"],
    queryFn: hakiApi.listMatters,
    enabled: hasApiConfiguration,
    retry: false,
  });
  const contacts = useQuery({
    queryKey: ["contacts"],
    queryFn: hakiApi.listContacts,
    enabled: hasApiConfiguration,
    retry: false,
  });
  const create = useMutation({
    mutationFn: () =>
      hakiApi.createSession({
        title: title.trim() || `New ${source === "mic" ? "recording" : "Omi session"}`,
        source,
        ...(language ? { language_hint: language } : {}),
      }),
    onSuccess: (session) => navigate({ to: "/sessions/$sessionId", params: { sessionId: session.id }, search: { fresh: true } }),
  });
  const showcase = useMutation({
    mutationFn: hakiApi.ensureShowcase,
    onSuccess: (session) => {
      void queryClient.invalidateQueries({ queryKey: ["sessions"] });
      void queryClient.invalidateQueries({ queryKey: ["matters"] });
      void queryClient.invalidateQueries({ queryKey: ["contacts"] });
      navigate({ to: "/sessions/$sessionId", params: { sessionId: session.id }, search: { fresh: false } });
    },
    onError: (error) => toast.error(error.message),
  });
  const health = useQuery({
    queryKey: ["health"],
    queryFn: hakiApi.health,
    enabled: hasApiConfiguration,
    retry: false,
  });

  const sessionCount = sessions.data?.length ?? 0;
  const matterCount = matters.data?.length ?? 0;
  const readyCount = sessions.data?.filter((session) => session.status === "ready" || session.status === "exported").length ?? 0;

  return (
    <PageShell>
      <main>
        <section className="relative border-b border-border/80">
          <div className="mx-auto grid max-w-6xl items-start gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[minmax(0,1fr)_24.5rem] lg:gap-14 lg:py-16">
            <div className="order-2 max-w-2xl animate-ink-rise lg:order-1">
              <SectionEyebrow>Conversation to legal work</SectionEyebrow>
              <h1 className="mt-4 font-serif text-4xl font-semibold leading-[1.12] tracking-tight text-foreground sm:text-6xl">
                Capture what matters.{" "}
                <em className="italic text-primary">Leave with work ready.</em>
              </h1>
              <p className="mt-5 max-w-xl text-base leading-7 text-muted-foreground sm:text-lg">
                An agent for the rooms where justice is spoken — not another chatbot. Record a meeting or proceeding, verify the record, then choose the work it prepares.
              </p>
              <ol className="mt-8 grid gap-3 sm:grid-cols-3">
                {practiceSteps.map((step) => (
                  <li key={step.n} className="rounded-xl border border-border/80 bg-card/80 p-4">
                    <p className="font-serif text-sm text-action">{step.n}</p>
                    <p className="mt-2 text-sm font-semibold text-foreground">{step.title}</p>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">{step.copy}</p>
                  </li>
                ))}
              </ol>
              <div className="mt-6 grid gap-3 sm:grid-cols-3">
                {environments.map((item) => (
                  <div key={item.place} className="rounded-xl border border-border/70 bg-background/70 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">{item.place}</p>
                    <p className="mt-1.5 text-sm font-semibold text-foreground">{item.title}</p>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.copy}</p>
                  </div>
                ))}
              </div>
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <TrustLine className="rounded-full border border-border bg-card/80 px-3 py-1.5" />
                <span className="rounded-full border border-border bg-card/80 px-3 py-1.5 text-xs text-muted-foreground">
                  English + Kiswahili
                </span>
              </div>
            </div>

            <div className="desk-card relative order-1 overflow-hidden rounded-2xl border border-border p-5 sm:p-6 lg:order-2">
              <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary via-action to-primary" />
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-serif text-2xl font-semibold">Start a session</h2>
                  <p className="mt-1 text-sm text-muted-foreground">No document choice needed. HakiScribe listens first.</p>
                </div>
                <span className="grid size-10 place-items-center rounded-full bg-action/12 text-action">
                  {source === "mic" ? <Mic className="size-4" /> : <Headphones className="size-4" />}
                </span>
              </div>
              <label className="mt-6 block text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground" htmlFor="session-title">Session title</label>
              <Input id="session-title" className="mt-2 h-11 bg-background" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Wanjiku client meeting" />
              <div className="mt-5 grid grid-cols-2 gap-1 rounded-lg bg-muted p-1" aria-label="Recording source">
                {(["mic", "omi"] as const).map((item) => {
                  const Icon = item === "mic" ? Mic : Headphones;
                  return (
                    <Button key={item} type="button" variant={source === item ? "default" : "ghost"} className="h-10 shadow-none" onClick={() => setSource(item)}>
                      <Icon />{item === "mic" ? "Microphone" : "Omi wearable"}
                    </Button>
                  );
                })}
              </div>
              <label className="mt-5 block text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground" htmlFor="language">Language</label>
              <select id="language" value={language} onChange={(event) => setLanguage(event.target.value)} className="mt-2 h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring">
                <option value="code-switch">English + Kiswahili</option>
                <option value="en">English</option>
                <option value="sw">Kiswahili</option>
              </select>
              {source === "omi" && (
                <p className="mt-4 rounded-lg border border-border bg-background px-3 py-2 text-xs leading-5 text-muted-foreground">
                  Pair the wearable after the session opens. Omi posts transcript segments to
                  {" "}
                  <code className="font-mono text-[11px]">/webhooks/omi?session_id=&lt;id&gt;</code>
                  . No need to look at the phone while you listen.
                </p>
              )}
              <Button variant="warm" size="lg" className="mt-6 h-14 w-full text-base" onClick={() => create.mutate()} disabled={create.isPending || !hasApiConfiguration}>
                <span className="size-2.5 animate-live-dot rounded-full bg-action-foreground" />
                {create.isPending ? "Opening session…" : source === "mic" ? "Start recording" : "Start listening via Omi"}
              </Button>
              <Button
                variant="outline"
                className="mt-2 h-11 w-full"
                onClick={() => showcase.mutate()}
                disabled={showcase.isPending || !hasApiConfiguration}
              >
                {showcase.isPending ? "Building the Wanjiru showcase…" : "Open a completed judge demo"}
              </Button>
              {create.error && <p className="mt-3 text-sm text-destructive">{create.error.message}</p>}
              {showcase.error && <p className="mt-3 text-sm text-destructive">{showcase.error.message}</p>}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
          {hasApiConfiguration && !sessions.error && (
            <div className="mb-10 grid gap-3 sm:grid-cols-3">
              {[
                { label: "Sessions in the library", value: sessions.isLoading ? "—" : String(sessionCount) },
                { label: "Matters on the desk", value: matters.isLoading ? "—" : String(matterCount) },
                { label: "Ready to reopen", value: sessions.isLoading ? "—" : String(readyCount) },
              ].map((stat) => (
                <div key={stat.label} className="chamber-card rounded-xl border border-border px-5 py-4">
                  <p className="font-serif text-3xl font-semibold tabular-nums">{stat.value}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.14em] text-muted-foreground">{stat.label}</p>
                </div>
              ))}
            </div>
          )}
          <SectionHeading
            eyebrow="Session library"
            title="Past sessions"
            action={sessions.data && <span className="text-sm text-muted-foreground">{sessions.data.length} total</span>}
          />
          {!hasApiConfiguration && <ConnectionError message="Add VITE_API_BASE_URL to connect the HakiScribe frontend to the FastAPI service." />}
          {sessions.error && <ConnectionError message={sessions.error.message} retry={() => void sessions.refetch()} />}
          {sessions.isLoading && <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-24 animate-pulse rounded-xl border border-border bg-card" />)}</div>}
          {sessions.data?.length === 0 && (
            <div className="chamber-card rounded-xl border border-dashed border-border py-14 text-center">
              <p className="font-serif text-xl">The library is empty</p>
              <p className="mt-2 text-sm text-muted-foreground">Open the completed Wanjiru client meeting, or start listening.</p>
              <Button className="mt-5" variant="outline" onClick={() => showcase.mutate()} disabled={showcase.isPending || !hasApiConfiguration}>
                {showcase.isPending ? "Building showcase…" : "Load judge demo"}
              </Button>
            </div>
          )}
          <div className="grid gap-3">
            {sessions.data?.map((session) => <SessionRow key={session.id} session={session} />)}
          </div>
          <NewsDesk />
          <LibraryMatters matters={matters.data ?? []} contacts={contacts.data ?? []} />
        </section>
      </main>
      {health.data?.integrations && (
        <div className="mx-auto max-w-6xl px-4 pb-4 sm:px-6">
          <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
            Live integrations
            {": "}
            {Object.entries(health.data.integrations)
              .filter(([, on]) => on)
              .map(([name]) => name)
              .join(" · ") || "local-only fallbacks"}
          </p>
        </div>
      )}
      <WorkspaceFooter />
    </PageShell>
  );
}

function SessionRow({ session }: { session: Session }) {
  const matterNames = session.matters?.map((matter) => matter.matter_name).filter(Boolean) ?? [];
  const contactNames = session.contacts?.map((contact) => contact.name).filter(Boolean) ?? [];
  return (
    <Link
      to="/sessions/$sessionId"
      params={{ sessionId: session.id }}
      search={{ fresh: false }}
      className="chamber-card group grid grid-cols-[auto_1fr_auto] items-center gap-4 rounded-xl border border-border p-4 transition-all hover:-translate-y-0.5 hover:border-primary/30 sm:px-5"
    >
      <span className="grid size-12 place-items-center rounded-xl bg-secondary text-secondary-foreground">
        <SourceIcon source={session.source} className="size-4" />
      </span>
      <span className="min-w-0">
        <span className="block truncate font-medium text-foreground group-hover:text-primary">{session.title}</span>
        <span className="mt-1 block text-xs text-muted-foreground">
          {new Date(session.created_at).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}
          {" · "}
          {session.source === "omi" ? "Omi wearable" : "Microphone"}
        </span>
        {(matterNames.length > 0 || contactNames.length > 0 || (session.generated_types?.length ?? 0) > 0) && (
          <span className="mt-2 flex flex-wrap gap-1.5">
            {session.generated_types?.map((type) => {
              const Icon = actionIcons[type];
              return (
                <Badge key={type} variant="outline" className="gap-1 capitalize">
                  <Icon className="size-3" />
                  {type.replaceAll("_", " ")}
                </Badge>
              );
            })}
            {matterNames.map((name) => <Badge key={name} variant="secondary">{name}</Badge>)}
            {contactNames.map((name) => <Badge key={name} variant="outline">{name}</Badge>)}
          </span>
        )}
      </span>
      <StatusBadge status={session.status} />
    </Link>
  );
}

function LibraryMatters({ matters, contacts }: { matters: Matter[]; contacts: Contact[] }) {
  const contactsByMatter = (matterId: string) => contacts.filter((contact) => contact.matter_id === matterId);
  return (
    <div className="mt-16">
      <SectionHeading
        eyebrow="Workspace"
        title="Matters and contacts"
        action={<span className="text-sm text-muted-foreground">{matters.length} matter{matters.length === 1 ? "" : "s"}</span>}
      />
      {matters.length === 0 && (
        <div className="chamber-card rounded-xl border border-dashed border-border py-12 text-center text-muted-foreground">
          Generated workspace matters and linked contacts will persist here.
        </div>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        {matters.map((matter) => {
          const linked = contactsByMatter(matter.id);
          const initials = matter.client_name.split(" ").filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
          return (
            <article key={matter.id} className="chamber-card rounded-xl border border-border p-5">
              <div className="flex items-start gap-3">
                <span className="grid size-12 place-items-center rounded-xl bg-primary text-sm font-semibold text-primary-foreground">
                  {initials || <BriefcaseBusiness className="size-4" />}
                </span>
                <div className="min-w-0">
                  <h3 className="font-semibold text-foreground">{matter.matter_name}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">Client: {matter.client_name}</p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {linked.length === 0 && <span className="text-xs text-muted-foreground">No linked contacts yet</span>}
                    {linked.map((contact) => <Badge key={contact.id} variant="outline">{contact.name}</Badge>)}
                  </div>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

type FlowStep = "recording" | "speakers" | "redact" | "analyzing" | "tray" | "results";

export function SessionPage({ sessionId, fresh }: { sessionId: string; fresh: boolean }) {
  const queryClient = useQueryClient();
  const detail = useQuery({ queryKey: ["session", sessionId], queryFn: () => hakiApi.getSession(sessionId), retry: false });
  const [step, setStep] = useState<FlowStep | null>(null);
  useEffect(() => {
    if (!detail.data || step) return;
    const data = detail.data;
    const hasTranscript = Boolean(data.transcript?.length);
    const hasActions = Boolean(data.detected_actions?.length);
    const hasResults = Boolean(data.action_results?.length);
    if (fresh && data.status === "recording" && !hasTranscript) setStep("recording");
    else if (hasResults && !fresh) setStep("results");
    else if (hasActions) setStep("tray");
    else if (data.status === "recording" && !hasTranscript) setStep("recording");
    else if (hasTranscript && !hasActions) setStep("speakers");
    else setStep("analyzing");
  }, [detail.data, fresh, step]);

  if (detail.isLoading || !step) return <PageShell back><main className="mx-auto max-w-4xl px-4 py-24"><div className="mx-auto h-1 w-48 origin-left animate-reading-line bg-primary" /><p className="mt-6 text-center font-serif text-xl">Opening secure session…</p></main></PageShell>;
  if (detail.error || !detail.data) return <PageShell back><main className="mx-auto max-w-3xl px-4 py-16"><ConnectionError message={detail.error?.message ?? "Session not found"} retry={() => void detail.refetch()} /></main></PageShell>;

  const session = detail.data;
  if (step === "recording") return <RecordingScreen session={session} onStopped={(next) => { queryClient.setQueryData(["session", sessionId], next); setStep("speakers"); }} />;
  if (step === "speakers") return <SpeakerScreen session={session} onNext={async () => { await detail.refetch(); setStep("redact"); }} />;
  if (step === "redact") return <RedactScreen session={session} onNext={() => setStep("analyzing")} />;
  if (step === "analyzing") return <AnalyzingScreen sessionId={session.id} onComplete={async (actions) => {
    queryClient.setQueryData(["session", sessionId], (current: SessionDetail | undefined) => current ? { ...current, detected_actions: actions } : current);
    await detail.refetch();
    setStep("tray");
  }} />;
  return <PageShell back><ActionWorkspace session={session} initialResults={session.action_results ?? []} showResults={step === "results"} onResults={() => setStep("results")} onTray={() => setStep("tray")} onVerify={() => setStep("speakers")} /></PageShell>;
}

function RecordingScreen({ session, onStopped }: { session: SessionDetail; onStopped: (detail: SessionDetail) => void }) {
  const startedAt = useRef(Date.now());
  const recorder = useRef<MediaRecorder | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const stopping = useRef(false);
  const [elapsed, setElapsed] = useState(0);
  const [captions, setCaptions] = useState(session.transcript ?? []);
  const [flags, setFlags] = useState(session.flagged_moments ?? []);
  const [error, setError] = useState<string | null>(null);
  const [stoppingNow, setStoppingNow] = useState(false);

  useEffect(() => {
    const timer = window.setInterval(() => setElapsed(Date.now() - startedAt.current), 1000);
    if (session.source === "mic") {
      void navigator.mediaDevices.getUserMedia({ audio: true }).then((mediaStream) => {
        stream.current = mediaStream;
        const ws = new WebSocket(websocketUrl(session.id));
        socket.current = ws;
        ws.onmessage = (event) => {
          try { setCaptions((current) => [...current, JSON.parse(event.data as string) as TranscriptSegment]); } catch { setError("A transcript update could not be read."); }
        };
        ws.onerror = () => { if (!stopping.current) setError("Live transcription disconnected. Your session remains open."); };
        ws.onopen = () => {
          const nextRecorder = new MediaRecorder(mediaStream);
          recorder.current = nextRecorder;
          nextRecorder.ondataavailable = (event) => { if (event.data.size && ws.readyState === WebSocket.OPEN) ws.send(event.data); };
          // Backend timestamps each chunk as 3s — keep the client in step.
          nextRecorder.start(3000);
        };
      }).catch(() => setError("Microphone access is required for a Mic session. Allow access, then reopen this session."));
    } else {
      const poll = window.setInterval(() => {
        void hakiApi.getSession(session.id).then((next) => {
          setCaptions(next.transcript ?? []);
          setFlags(next.flagged_moments ?? []);
        }).catch(() => undefined);
      }, 4000);
      return () => {
        window.clearInterval(timer);
        window.clearInterval(poll);
      };
    }
    return () => {
      window.clearInterval(timer);
      stopping.current = true;
      if (recorder.current?.state === "recording") recorder.current.stop();
      socket.current?.close();
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, [session.id, session.source]);

  const flag = async (label?: string) => {
    try {
      const moment = await hakiApi.flagMoment(session.id, { at_ms: elapsed, ...(label ? { label } : {}) });
      setFlags((current) => [...current, moment]);
      toast.success(label ? `Flagged: ${label}` : "Moment flagged");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "The moment could not be flagged."); }
  };
  const stop = async () => {
    setStoppingNow(true); stopping.current = true;
    if (recorder.current?.state === "recording") recorder.current.stop();
    socket.current?.close(); stream.current?.getTracks().forEach((track) => track.stop());
    try { onStopped(await hakiApi.getSession(session.id)); } catch (caught) { setError(caught instanceof Error ? caught.message : "The session could not be loaded."); setStoppingNow(false); }
  };

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-primary text-primary-foreground">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_18%,oklch(1_0_0/0.08),transparent_42%)]" />
      <header className="relative z-10 flex items-center justify-between border-b border-primary-foreground/15 px-4 py-4 sm:px-8">
        <span className="font-serif text-xl font-semibold">HakiScribe</span>
        <span className="inline-flex items-center gap-2 rounded-full border border-primary-foreground/20 bg-primary-foreground/10 px-3 py-1 text-xs">
          <span className="size-2 animate-live-dot rounded-full bg-action" /> Recording
        </span>
      </header>
      <main className="relative z-10 mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-8 sm:px-8">
        <div className="text-center">
          <p className="text-sm text-primary-foreground/70">{session.title}</p>
          <div className="relative mx-auto mt-5 grid size-44 place-items-center sm:size-52">
            <span className="absolute inset-0 rounded-full border border-primary-foreground/15 animate-pulse-ring" />
            <span className="absolute inset-4 rounded-full border border-primary-foreground/10" />
            <p className="relative font-mono text-5xl tabular-nums sm:text-6xl">{formatDuration(elapsed)}</p>
          </div>
        </div>
        <div className="mt-6 flex min-h-8 gap-2 overflow-x-auto pb-2">
          {flags.map((item) => (
            <span key={item.id} className="shrink-0 rounded-full border border-primary-foreground/20 bg-primary-foreground/10 px-3 py-1.5 text-xs">
              {formatDuration(item.at_ms)} · {item.label ?? "Flagged moment"}
            </span>
          ))}
        </div>
        <div className="my-7 flex h-24 items-center justify-center gap-1" aria-label="Live audio waveform">
          {Array.from({ length: 32 }, (_, index) => (
            <span
              key={index}
              className={cn(
                "h-16 w-1 rounded-full bg-primary-foreground/75 animate-waveform",
                index % 3 === 1 && "[animation-delay:180ms]",
                index % 3 === 2 && "[animation-delay:360ms]",
              )}
            />
          ))}
        </div>
        <div className="mb-3 flex flex-wrap justify-center gap-2">
          {flagLabels.map((label) => (
            <Button key={label} variant="quiet" size="sm" className="border-primary-foreground/20 bg-primary-foreground/10 text-primary-foreground hover:bg-primary-foreground/20" onClick={() => void flag(label)}>
              {label}
            </Button>
          ))}
        </div>
        <Button variant="warm" className="mx-auto h-24 w-full max-w-md text-xl shadow-lg" onClick={() => void flag()}>
          <Flag className="size-7" /> Flag this moment
        </Button>
        <div className="mt-8 min-h-24 rounded-xl border border-primary-foreground/10 bg-primary-foreground/5 px-4 py-4">
          {session.source === "omi" && !captions.length ? (
            <div className="space-y-3 text-sm text-primary-foreground/80">
              <p className="flex items-center justify-center gap-2">
                <Radio className="size-4" /> Listening via Omi. Incoming segments appear here.
              </p>
              <p className="break-all rounded-md bg-primary-foreground/8 px-3 py-2 font-mono text-[11px] text-primary-foreground/70">
                {omiWebhookUrl(session.id)}
              </p>
              <div className="flex justify-center">
                <Button
                  variant="quiet"
                  size="sm"
                  className="border-primary-foreground/20 bg-primary-foreground/10 text-primary-foreground hover:bg-primary-foreground/20"
                  onClick={() => {
                    void navigator.clipboard.writeText(omiWebhookUrl(session.id));
                    toast.success("Omi webhook copied");
                  }}
                >
                  <Copy /> Copy pairing URL
                </Button>
              </div>
            </div>
          ) : (
            <div className="max-h-28 space-y-2 overflow-y-auto text-sm italic text-primary-foreground/65">
              {captions.slice(-4).map((line) => (
                <p key={line.id}><span className="font-semibold not-italic">{line.speaker ?? "Speaker"}:</span> {line.text}</p>
              ))}
              {!captions.length && <p className="text-center">Live captions will appear here as people speak.</p>}
            </div>
          )}
        </div>
        {error && <p className="mt-4 text-center text-sm text-primary-foreground">{error}</p>}
        <div className="mt-auto flex flex-col items-center pt-8">
          <Button variant="quiet" className="h-12 min-w-36 border-primary-foreground/25 bg-primary-foreground/10 text-primary-foreground hover:bg-primary-foreground/20" onClick={() => void stop()} disabled={stoppingNow}>
            <Square className="fill-current" /> {stoppingNow ? "Stopping…" : "Stop"}
          </Button>
          <TrustLine className="mt-5 text-primary-foreground/65 [&_svg]:text-primary-foreground" />
        </div>
      </main>
    </div>
  );
}

function FlaggedMomentsBar({ flags }: { flags: FlaggedMoment[] }) {
  if (!flags.length) return null;
  return (
    <div className="mb-6 rounded-xl border border-border bg-card px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Flagged in the room</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {flags.map((flag) => (
          <Badge key={flag.id} variant="secondary">
            <Flag className="size-3" />
            {formatDuration(flag.at_ms)}
            {flag.label ? ` · ${flag.label}` : ""}
          </Badge>
        ))}
      </div>
    </div>
  );
}

function FlowHeader({ step, title, copy }: { step: string; title: string; copy: string }) {
  return (
    <div className="mb-8">
      <SectionEyebrow>{step}</SectionEyebrow>
      <h1 className="mt-2 font-serif text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h1>
      <p className="mt-3 max-w-2xl leading-7 text-muted-foreground">{copy}</p>
    </div>
  );
}

function SpeakerScreen({ session, onNext }: { session: SessionDetail; onNext: () => void }) {
  const speakers = useMemo(() => Array.from(new Set(session.transcript.map((s) => s.speaker).filter((s): s is string => Boolean(s)))), [session.transcript]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const mutation = useMutation({ mutationFn: () => hakiApi.updateSpeakers(session.id, mapping), onSuccess: onNext });
  return (
    <PageShell back>
      <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <FlowProgress current={1} labels={["Speakers", "Privilege", "Actions"]} />
        <FlowHeader step="Verify the record" title="Who was speaking?" copy="Names entered here flow into legal documents. Review them deliberately, or keep the original labels." />
        <div className="chamber-card divide-y divide-border overflow-hidden rounded-xl border border-border">
          {speakers.map((speaker) => (
            <div key={speaker} className="grid gap-2 px-4 py-5 sm:grid-cols-[10rem_1fr] sm:items-center">
              <label className="text-sm font-semibold" htmlFor={`speaker-${speaker}`}>{speaker}</label>
              <Input id={`speaker-${speaker}`} className="h-11 bg-background" placeholder="Type their real name" value={mapping[speaker] ?? ""} onChange={(event) => setMapping((current) => ({ ...current, [speaker]: event.target.value }))} />
            </div>
          ))}
        </div>
        {!speakers.length && <p className="chamber-card rounded-xl border border-dashed border-border py-8 text-center text-muted-foreground">No speaker labels were found. You can continue to the transcript check.</p>}
        {mutation.error && <p className="mt-4 text-sm text-destructive">{mutation.error.message}</p>}
        <div className="mt-8 flex justify-end gap-3">
          <Button variant="ghost" onClick={onNext}>Skip</Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !Object.values(mapping).some((name) => name.trim())}>
            {mutation.isPending ? "Saving…" : "Save names"}
          </Button>
        </div>
      </main>
    </PageShell>
  );
}

function RedactScreen({ session, onNext }: { session: SessionDetail; onNext: () => void }) {
  const queryClient = useQueryClient();
  const [segments, setSegments] = useState(session.transcript);
  const [error, setError] = useState<string | null>(null);
  const toggle = async (segment: TranscriptSegment) => {
    const nextValue = !segment.redacted;
    setSegments((current) => current.map((item) => item.id === segment.id ? { ...item, redacted: nextValue } : item));
    try { await hakiApi.redactSegment(session.id, segment.id, nextValue); }
    catch (caught) { setSegments((current) => current.map((item) => item.id === segment.id ? segment : item)); setError(caught instanceof Error ? caught.message : "The privacy setting could not be changed."); }
  };
  const continueFlow = async () => { await queryClient.invalidateQueries({ queryKey: ["session", session.id] }); onNext(); };
  return (
    <PageShell back>
      <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
        <FlowProgress current={2} labels={["Speakers", "Privilege", "Actions"]} />
        <FlowHeader step="Verify the record" title="Protect what stays private" copy="Lock any privileged or off-record line. It stays visible to you, but will not be sent for analysis." />
        <FlaggedMomentsBar flags={session.flagged_moments} />
        {error && <ConnectionError message={error} />}
        <div className="chamber-card mt-2 divide-y divide-border overflow-hidden rounded-xl border border-border">
          {segments.map((segment) => (
            <div key={segment.id} className={cn("grid grid-cols-[1fr_auto] gap-4 px-4 py-4 sm:px-5", segment.redacted && "bg-privileged/70 text-muted-foreground")}>
              <div>
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold text-primary">{segment.speaker ?? "Speaker"}</span>
                  <span className="font-mono text-[11px] text-muted-foreground">{formatDuration(segment.start_ms)}</span>
                  {segment.redacted && <Badge variant="outline" className="border-privileged-foreground/30 text-privileged-foreground">Won't be used</Badge>}
                </div>
                <p className={cn("font-serif text-base leading-7", segment.redacted && "line-through decoration-privileged-foreground/50")}>{segment.text}</p>
              </div>
              <Button variant="ghost" size="icon" aria-label={segment.redacted ? "Include this line" : "Mark privileged"} title={segment.redacted ? "Include this line" : "Mark privileged"} onClick={() => void toggle(segment)}>
                {segment.redacted ? <LockKeyhole className="text-privileged-foreground" /> : <UnlockKeyhole />}
              </Button>
            </div>
          ))}
        </div>
        {!segments.length && <p className="chamber-card rounded-xl border border-dashed border-border py-10 text-center text-muted-foreground">No transcript segments have arrived yet. You can still continue and analyze the available session data.</p>}
        <div className="sticky bottom-0 mt-6 border-t border-border bg-background/90 py-4 text-right backdrop-blur-md">
          <Button size="lg" onClick={() => void continueFlow()}>Continue to analysis</Button>
        </div>
      </main>
    </PageShell>
  );
}

function AnalyzingScreen({ sessionId, onComplete }: { sessionId: string; onComplete: (actions: DetectedAction[]) => void }) {
  const [error, setError] = useState<string | null>(null);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;
  useEffect(() => {
    let active = true;
    void hakiApi.finalize(sessionId).then(() => hakiApi.detect(sessionId)).then((actions) => { if (active) void onCompleteRef.current(actions); }).catch((caught) => { if (active) setError(caught instanceof Error ? caught.message : "Analysis could not be completed."); });
    return () => { active = false; };
  }, [sessionId]);
  return (
    <PageShell back>
      <main className="mx-auto flex min-h-[70vh] max-w-xl flex-col items-center justify-center px-5 text-center">
        <FlowProgress current={3} labels={["Speakers", "Privilege", "Actions"]} />
        <div className="w-48 space-y-2" aria-hidden>
          {[0, 1, 2, 3].map((item) => (
            <div key={item} className="h-1 origin-left animate-reading-line bg-primary" style={{ animationDelay: `${item * 220}ms` }} />
          ))}
        </div>
        <h1 className="mt-10 font-serif text-3xl font-semibold">Reviewing what happened…</h1>
        <p className="mt-3 leading-7 text-muted-foreground">Checking the verified record for documents, dates, matters, contacts, notes, and billable work. Flagged moments are weighed first. Redacted lines stay out.</p>
        <TrustLine className="mt-5" />
        {error && <div className="mt-8 w-full"><ConnectionError message={error} retry={() => window.location.reload()} /></div>}
      </main>
    </PageShell>
  );
}

function ActionWorkspace({ session, initialResults, showResults, onResults, onTray, onVerify }: { session: SessionDetail; initialResults: ActionResult[]; showResults: boolean; onResults: () => void; onTray: () => void; onVerify: () => void }) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"tray" | "record" | "results">(showResults ? "results" : "tray");
  const [selected, setSelected] = useState(() => new Set(session.detected_actions.filter((action) => action.pre_checked && action.status !== "dismissed").map((action) => action.id)));
  const [actions, setActions] = useState(session.detected_actions);
  const [results, setResults] = useState(initialResults);
  const [showDismissed, setShowDismissed] = useState(false);
  useEffect(() => {
    setActions(session.detected_actions);
    setSelected(new Set(session.detected_actions.filter((action) => action.pre_checked && action.status !== "dismissed").map((action) => action.id)));
  }, [session.detected_actions]);
  useEffect(() => {
    if (initialResults.length) setResults(initialResults);
  }, [initialResults]);
  useEffect(() => {
    setTab(showResults ? "results" : "tray");
  }, [showResults]);
  const visibleActions = actions.filter((action) => showDismissed || action.status !== "dismissed");
  const failedIds = results.filter((item) => item.status === "error").map((item) => item.action_id);
  const generate = useMutation({
    mutationFn: (ids: string[]) => {
      const fieldOverrides = Object.fromEntries(
        actions.filter((action) => ids.includes(action.id)).map((action) => [action.id, action.extracted_fields]),
      );
      return hakiApi.generate(session.id, ids, fieldOverrides);
    },
    onSuccess: (data) => {
      setResults((current) => {
        const merged = new Map(current.map((item) => [item.action_id, item]));
        for (const item of data) merged.set(item.action_id, item);
        return Array.from(merged.values());
      });
      onResults();
      toast.success("Selected work is ready to review.");
      void queryClient.invalidateQueries({ queryKey: ["sessions"] });
      void queryClient.invalidateQueries({ queryKey: ["session", session.id] });
      void queryClient.invalidateQueries({ queryKey: ["matters"] });
      void queryClient.invalidateQueries({ queryKey: ["contacts"] });
    },
  });
  const select = (id: string, checked: boolean) => setSelected((current) => { const next = new Set(current); checked ? next.add(id) : next.delete(id); return next; });
  const dismiss = async (id: string) => {
    try {
      const next = await hakiApi.dismissAction(session.id, id);
      setActions((current) => current.map((item) => item.id === id ? next : item));
      select(id, false);
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : "The action could not be dismissed.");
    }
  };
  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <div className="flex flex-col justify-between gap-5 border-b border-border pb-8 sm:flex-row sm:items-end">
        <div>
          <SectionEyebrow>{tab === "results" ? "Generated work" : tab === "record" ? "Verified record" : "Action tray"}</SectionEyebrow>
          <h1 className="mt-2 font-serif text-3xl font-semibold tracking-tight sm:text-4xl">{session.title}</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {tab === "results" ? "Review and edit before anything leaves your workspace." : tab === "record" ? "The same record the tray used, including what you locked." : `${visibleActions.length} possible legal actions, each grounded in the transcript.`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={onVerify}>Back to verify</Button>
          <TrustLine className="rounded-full border border-border bg-card px-3 py-1.5" />
        </div>
      </div>
      <FlaggedMomentsBar flags={session.flagged_moments} />
      <div className="mt-6 flex flex-wrap gap-2 rounded-lg bg-muted p-1">
        <Button variant={tab === "tray" ? "default" : "ghost"} className="shadow-none" onClick={() => { setTab("tray"); onTray(); }}>Detected actions</Button>
        <Button variant={tab === "record" ? "default" : "ghost"} className="shadow-none" onClick={() => setTab("record")}>Transcript</Button>
        {results.length > 0 && <Button variant={tab === "results" ? "default" : "ghost"} className="shadow-none" onClick={() => { setTab("results"); onResults(); }}>Results ({results.length})</Button>}
      </div>
      {tab === "record" ? (
        <TranscriptPanel transcript={session.transcript} actions={visibleActions} />
      ) : tab === "results" && results.length ? (
        <>
          <ResultsList results={results} />
          {failedIds.length > 0 && (
            <div className="mt-6">
              <Button variant="outline" disabled={generate.isPending} onClick={() => generate.mutate(failedIds)}>
                Retry failed ({failedIds.length})
              </Button>
            </div>
          )}
        </>
      ) : (
        <>
          <div className="my-6 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">Review, edit, then choose what HakiScribe should produce.</p>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowDismissed((current) => !current)}>
                {showDismissed ? "Hide dismissed" : "Show dismissed"}
              </Button>
              <Button variant="outline" size="sm" onClick={() => setSelected(new Set(visibleActions.filter((action) => action.pre_checked).map((action) => action.id)))}>
                <Check /> Select high-confidence
              </Button>
            </div>
          </div>
          <div className="space-y-3">
            {visibleActions.map((action) => (
              <ActionCard
                key={action.id}
                action={action}
                transcript={session.transcript}
                flags={session.flagged_moments}
                checked={selected.has(action.id)}
                onChecked={(checked) => select(action.id, checked)}
                onDismiss={() => void dismiss(action.id)}
                onFields={(fields) => setActions((current) => current.map((item) => item.id === action.id ? { ...item, extracted_fields: fields } : item))}
              />
            ))}
          </div>
          {!visibleActions.length && (
            <div className="chamber-card rounded-xl border border-dashed border-border py-12 text-center">
              <h2 className="font-serif text-2xl">No actions detected</h2>
              <p className="mt-2 text-muted-foreground">The verified transcript did not contain enough information to propose legal work.</p>
            </div>
          )}
          <article className="chamber-card mt-3 rounded-xl border border-border bg-card">
            <div className="grid grid-cols-[auto_1fr] gap-3 p-4 sm:p-5">
              <span className="grid size-11 place-items-center rounded-xl bg-secondary text-secondary-foreground"><Scale className="size-5" /></span>
              <div className="min-w-0">
                <h2 className="font-semibold text-foreground">Kenyan legal research on this matter</h2>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  Case law, statutes and precedent for the issues raised on this record, each with a citation you can open.
                </p>
                <Button asChild variant="outline" size="sm" className="mt-3">
                  <Link to="/research" search={{ session: session.id }}>Open research</Link>
                </Button>
              </div>
            </div>
          </article>
          <AskComposer
            sessionId={session.id}
            onResult={(result) => {
              setResults((current) => [result, ...current.filter((item) => item.action_id !== result.action_id)]);
              void queryClient.invalidateQueries({ queryKey: ["session", session.id] });
              onResults();
            }}
          />
          <NewsDesk topic={session.matters?.[0]?.matter_name || session.title} />
          {generate.error && <div className="mt-5"><ConnectionError message={generate.error.message} /></div>}
          <div className="sticky bottom-0 mt-8 border-t border-border bg-background/90 py-4 backdrop-blur-md">
            <Button variant="warm" size="lg" className="h-12 w-full" disabled={!selected.size || generate.isPending} onClick={() => generate.mutate(Array.from(selected))}>
              {generate.isPending ? "Generating selected work…" : `Generate selected (${selected.size})`}
            </Button>
          </div>
        </>
      )}
    </main>
  );
}

function TranscriptPanel({ transcript, actions }: { transcript: TranscriptSegment[]; actions: DetectedAction[] }) {
  const cited = new Set(actions.map((action) => action.source_segment_id).filter(Boolean));
  return (
    <div className="chamber-card mt-8 divide-y divide-border overflow-hidden rounded-xl border border-border">
      {transcript.map((segment) => (
        <div key={segment.id} className={cn("px-4 py-4 sm:px-5", segment.redacted && "bg-privileged/70 text-muted-foreground", cited.has(segment.id) && !segment.redacted && "bg-secondary/40")}>
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-primary">{segment.speaker ?? "Speaker"}</span>
            <span className="font-mono text-[11px] text-muted-foreground">{formatDuration(segment.start_ms)}</span>
            {segment.redacted && <Badge variant="outline" className="border-privileged-foreground/30 text-privileged-foreground">Won't be used</Badge>}
            {cited.has(segment.id) && !segment.redacted && <Badge variant="secondary">Cited in tray</Badge>}
          </div>
          <p className={cn("font-serif text-base leading-7", segment.redacted && "line-through decoration-privileged-foreground/50")}>{segment.text}</p>
        </div>
      ))}
      {!transcript.length && <p className="px-4 py-10 text-center text-muted-foreground">No transcript segments are available.</p>}
    </div>
  );
}

function nearestFlag(flags: FlaggedMoment[], source: TranscriptSegment | undefined) {
  if (!source) return undefined;
  return flags.find((flag) => Math.abs(flag.at_ms - source.start_ms) <= 8000);
}

function ActionCard({ action, transcript, flags, checked, onChecked, onDismiss, onFields }: { action: DetectedAction; transcript: TranscriptSegment[]; flags: FlaggedMoment[]; checked: boolean; onChecked: (checked: boolean) => void; onDismiss: () => void; onFields: (fields: Record<string, unknown>) => void }) {
  const [open, setOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(false);
  const Icon = actionIcons[action.type];
  const source = transcript.find((segment) => segment.id === action.source_segment_id);
  const flagged = nearestFlag(flags, source);
  const speculative = !action.pre_checked || action.confidence < 0.7;
  const background = action.extracted_fields["background_info"];
  const detectionMode = action.extracted_fields["detection_mode"];
  return (
    <article className={cn(
      "chamber-card overflow-hidden rounded-xl border transition-all",
      checked ? "border-primary bg-secondary/20" : "border-border bg-card",
      speculative && !checked && "opacity-70",
      action.status === "dismissed" && "opacity-50",
    )}>
      <div className="grid grid-cols-[auto_1fr_auto] gap-3 p-4 sm:p-5">
        <span className="grid size-11 place-items-center rounded-xl bg-secondary text-secondary-foreground"><Icon className="size-5" /></span>
        <button type="button" className="min-w-0 text-left" onClick={() => setOpen(!open)}>
          <h2 className="font-semibold text-foreground">{action.title}</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{action.preview}</p>
        </button>
        <Checkbox checked={checked} onCheckedChange={(value) => onChecked(value === true)} aria-label={`Select ${action.title}`} className="mt-2 size-5" disabled={action.status === "dismissed"} />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/80 px-4 py-3 text-xs sm:px-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={speculative ? "outline" : "secondary"}>{action.confidence_reason ?? `${Math.round(action.confidence * 100)}% confidence`}</Badge>
          {flagged && <Badge variant="secondary">Honours flag{flagged.label ? `: ${flagged.label}` : ""}</Badge>}
          {detectionMode === "heuristic" && <Badge variant="outline">From the record</Badge>}
          {background !== undefined && <Badge variant="outline">External research</Badge>}
        </div>
        <div className="flex items-center gap-3">
          {source && <button type="button" className="font-semibold text-primary hover:underline" onClick={() => setSourceOpen(!sourceOpen)}>View source</button>}
          {action.status !== "dismissed" && <button type="button" className="text-muted-foreground hover:text-foreground" onClick={onDismiss}>Dismiss</button>}
          <button type="button" aria-label={open ? "Collapse action" : "Edit action"} onClick={() => setOpen(!open)}>
            <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
          </button>
        </div>
      </div>
      {sourceOpen && source && (
        <div className="border-t border-border bg-secondary/35 px-4 py-4 sm:px-5">
          <p className="mb-1 text-xs font-semibold text-primary">{source.speaker ?? "Speaker"} · {formatDuration(source.start_ms)}</p>
          <blockquote className="font-serif leading-7">“{source.text}”</blockquote>
        </div>
      )}
      {background !== undefined && (
        <div className="border-t border-border bg-muted/40 px-4 py-3 text-xs leading-5 text-muted-foreground sm:px-5">
          External research — not from the record. {typeof background === "string" ? background : displayValue(background)}
        </div>
      )}
      {open && (
        <div className="grid gap-4 border-t border-border p-4 sm:grid-cols-2 sm:p-5">
          {Object.entries(action.extracted_fields).filter(([key]) => !hiddenFieldKeys.has(key)).map(([key, value]) => (
            <label key={key} className={cn("text-xs font-semibold capitalize text-muted-foreground", typeof value === "object" && "sm:col-span-2")}>
              {key.replaceAll("_", " ")}
              {typeof value === "object" ? (
                <Textarea className="mt-2 min-h-24 bg-background font-mono text-xs" value={displayValue(value)} onChange={(event) => onFields({ ...action.extracted_fields, [key]: event.target.value })} />
              ) : (
                <Input className="mt-2 bg-background text-foreground" value={displayValue(value)} onChange={(event) => onFields({ ...action.extracted_fields, [key]: event.target.value })} />
              )}
            </label>
          ))}
        </div>
      )}
    </article>
  );
}

function AskComposer({ sessionId, onResult }: { sessionId: string; onResult: (result: ActionResult) => void }) {
  const [instruction, setInstruction] = useState("");
  const catalogue = useQuery({ queryKey: ["models"], queryFn: hakiApi.listModels, retry: false });
  const [model, setModel] = useState("");
  const ask = useMutation({
    mutationFn: () => hakiApi.ask(sessionId, { instruction: instruction.trim(), ...(model ? { model } : {}) }),
    onSuccess: (result) => { setInstruction(""); onResult(result); },
  });
  const suggestions = [
    "Summarise this meeting for the partner in five bullet points.",
    "List every commitment my client made and its deadline.",
    "Draft talking points for the next mention.",
  ];
  return (
    <section className="chamber-card mt-8 rounded-xl border border-border p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <span className="grid size-11 place-items-center rounded-xl bg-secondary text-secondary-foreground"><Sparkles className="size-5" /></span>
        <div className="min-w-0">
          <h2 className="font-semibold text-foreground">Ask anything about this session</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Runs against the verified, non-redacted record only. Locked lines are never sent.
          </p>
        </div>
      </div>
      <Textarea
        aria-label="Instruction for this session"
        className="mt-4 min-h-24 bg-background"
        placeholder="e.g. List every deadline agreed on the record"
        value={instruction}
        onChange={(event) => setInstruction(event.target.value)}
      />
      <div className="mt-2 flex flex-wrap gap-2">
        {suggestions.map((item) => (
          <button key={item} type="button" className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground" onClick={() => setInstruction(item)}>
            {item}
          </button>
        ))}
      </div>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <label className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          Model
          <select
            className="mt-2 block h-11 w-full rounded-md border border-input bg-background px-3 text-sm font-normal normal-case tracking-normal text-foreground outline-none focus:ring-1 focus:ring-ring sm:w-64"
            value={model}
            onChange={(event) => setModel(event.target.value)}
          >
            <option value="">{catalogue.data ? `Default (${catalogue.data.default})` : "Default"}</option>
            {catalogue.data?.models.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
          </select>
        </label>
        <Button className="h-11 sm:self-end" disabled={!instruction.trim() || ask.isPending} onClick={() => ask.mutate()}>
          {ask.isPending ? "Working…" : "Run on this session"}
        </Button>
      </div>
      {catalogue.data?.configured === false && (
        <p className="mt-3 text-xs text-muted-foreground">No language model is connected yet, so answers will explain that instead of guessing.</p>
      )}
      {ask.error && <p className="mt-3 text-sm text-destructive">{ask.error.message}</p>}
    </section>
  );
}

function NewsDesk({ topic }: { topic?: string }) {
  const news = useQuery({ queryKey: ["news"], queryFn: hakiApi.listNews, enabled: hasApiConfiguration, retry: false });
  const watch = useMutation({
    mutationFn: () => hakiApi.watchNews(topic?.trim() || "Kenya legal and commercial news"),
    onSuccess: (data) => {
      toast.success(data.created ? "News watch started" : "News watch refreshed");
      void news.refetch();
    },
    onError: (error) => toast.error(error.message),
  });
  const hits = news.data?.hits ?? [];
  return (
    <section className="chamber-card mt-10 rounded-xl border border-border p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">Web search & news</p>
          <h2 className="mt-1 font-serif text-xl font-semibold">Citation crawl and news monitoring</h2>
          <p className="mt-1 text-sm text-muted-foreground">Exa retrieves authorities and watches latest reporting. Hits stay labelled as background — never filed as fact.</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => watch.mutate()} disabled={watch.isPending || !hasApiConfiguration}>
          <Newspaper /> {watch.isPending ? "Searching…" : topic ? `Watch “${topic.slice(0, 40)}”` : "Watch Kenya legal news"}
        </Button>
      </div>
      {!hits.length && <p className="mt-4 text-sm text-muted-foreground">No monitor hits yet. Start a watch to pull the latest stories.</p>}
      <ol className="mt-4 space-y-3">
        {hits.slice(0, 6).map((hit: NewsHit, index) => (
          <li key={hit.id ?? hit.url ?? index} className="text-sm">
            {hit.url ? (
              <a href={hit.url} target="_blank" rel="noreferrer" className="font-medium text-primary hover:underline">{hit.title ?? hit.url}</a>
            ) : (
              <span className="font-medium">{hit.title ?? "Untitled"}</span>
            )}
            {hit.published && <span className="ml-2 text-xs text-muted-foreground">{hit.published.slice(0, 10)}</span>}
            {hit.extract && <p className="mt-1 text-xs leading-5 text-muted-foreground">{hit.extract}</p>}
          </li>
        ))}
      </ol>
    </section>
  );
}

function SourceList({ sources }: { sources: ResearchSource[] }) {
  if (!sources.length) return null;
  return (
    <ol className="mt-5 space-y-3 border-t border-border pt-4">
      {sources.map((source, index) => (
        <li key={`${source.url ?? index}`} className="text-sm">
          <span className="mr-2 font-mono text-xs text-muted-foreground">[{index + 1}]</span>
          {source.url ? (
            <a href={source.url} target="_blank" rel="noreferrer" className="font-medium text-primary hover:underline">{source.title ?? source.url}</a>
          ) : (
            <span className="font-medium">{source.title ?? "Untitled source"}</span>
          )}
          {source.citation && <span className="ml-2 text-xs text-muted-foreground">{source.citation}</span>}
          {source.kind && <Badge variant="outline" className="ml-2 capitalize">{source.kind}</Badge>}
          {source.published && <span className="ml-2 text-xs text-muted-foreground">{source.published.slice(0, 10)}</span>}
          {source.extract && <p className="mt-1 text-xs leading-5 text-muted-foreground">{source.extract}</p>}
        </li>
      ))}
    </ol>
  );
}

function ResultsList({ results }: { results: ActionResult[] }) {
  return <div className="mt-8 space-y-4">{results.map((item) => <ResultCard key={item.action_id} result={item} />)}</div>;
}

function ResultCard({ result }: { result: ActionResult }) {
  const Icon = actionIcons[result.type];
  const [documentText, setDocumentText] = useState(displayValue(result.result["document_text"] ?? ""));
  if (result.status === "error") {
    return (
      <article className="chamber-card rounded-xl border border-destructive/30 p-5">
        <div className="flex items-center gap-3">
          <AlertCircle className="size-5 text-destructive" />
          <div>
            <h2 className="font-semibold">This item was not generated</h2>
            <p className="mt-1 text-sm text-muted-foreground">{result.error ?? "The service returned an error for this item."}</p>
          </div>
        </div>
      </article>
    );
  }
  const calendarHref = typeof result.result["ics"] === "string" ? `data:text/calendar;charset=utf-8,${encodeURIComponent(result.result["ics"])}` : null;
  const workspaceUrl = typeof result.result["workspace_url"] === "string" ? result.result["workspace_url"] : null;
  const shareUrl = typeof result.result["whatsapp_share_url"] === "string"
    ? result.result["whatsapp_share_url"]
    : whatsappShareUrl(documentText || displayValue(result.result["note_text"] ?? result.result["narrative"] ?? result.result["description"] ?? result.result["matter_name"] ?? result.type));
  const hiddenResultKeys = new Set(["ics", "narrative", "description", "document_text", "note_text", "whatsapp_share_url", "whatsapp_share_text", "workspace_url"]);
  const title = result.type === "workspace_matter"
    ? `${result.result["note"] ? String(result.result["note"]).startsWith("linked") ? "Linked matter" : "New matter" : "Matter"}: ${displayValue(result.result["matter_name"])}`
    : result.type === "crm_entry"
      ? `Contact: ${displayValue(result.result["contact_name"])}`
      : result.type === "private_note"
        ? "Private note"
        : result.type === "time_entry"
          ? `${displayValue(result.result["duration_hours"])}h · ${displayValue(result.result["matter_name"] ?? "This session")}`
          : result.type.replaceAll("_", " ");
  const longText = result.type === "time_entry" ? displayValue(result.result["narrative"] ?? result.result["activity_description"] ?? "") : result.type === "calendar_event" ? displayValue(result.result["description"] ?? "") : result.type === "private_note" ? displayValue(result.result["note_text"] ?? "") : "";
  return (
    <article className="chamber-card overflow-hidden rounded-xl border border-border">
      <header className="flex items-center gap-3 border-b border-border px-4 py-4 sm:px-6">
        <span className="grid size-10 place-items-center rounded-xl bg-success text-success-foreground"><Icon className="size-4" /></span>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-success-foreground">Generated</p>
          <h2 className="font-semibold capitalize">{title}</h2>
        </div>
      </header>
      {result.type === "draft_document" ? (
        <div className="p-4 sm:p-8">
          <div className="mb-3 flex flex-wrap justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => { void navigator.clipboard.writeText(documentText); toast.success("Draft copied"); }}><Copy /> Copy</Button>
            <Button variant="outline" size="sm" onClick={() => { downloadTextFile("hakiscribe-draft.txt", documentText); toast.success("Draft downloaded"); }}><Download /> Download</Button>
            <Button asChild variant="outline" size="sm"><a href={shareUrl} target="_blank" rel="noreferrer"><MessageCircle /> WhatsApp review</a></Button>
            {(workspaceUrl || typeof result.result["ambiguous_document_url"] === "string") && (
              <Button asChild variant="outline" size="sm">
                <a href={(workspaceUrl || result.result["ambiguous_document_url"]) as string} target="_blank" rel="noreferrer"><FileText /> Open in Ambiguous</a>
              </Button>
            )}
          </div>
          <Textarea aria-label="Editable legal document" value={documentText} onChange={(event) => setDocumentText(event.target.value)} className="min-h-[28rem] resize-y border-0 bg-background p-6 font-serif text-base leading-8 shadow-none focus-visible:ring-1 sm:p-10" />
        </div>
      ) : result.type === "legal_research" || result.type === "web_search" ? (
        <div className="p-5 sm:p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            {result.type === "legal_research" ? "Question researched" : "Background check"}
          </p>
          <p className="mt-1 font-serif text-lg leading-7">{displayValue(result.result["question"])}</p>
          <p className="mt-4 whitespace-pre-wrap text-sm leading-7">{displayValue(result.result["answer"])}</p>
          <SourceList sources={(result.result["sources"] as ResearchSource[] | undefined) ?? []} />
          <p className="mt-4 text-xs text-muted-foreground">
            {result.type === "legal_research"
              ? "Check every authority before relying on it. Research is never merged into a draft."
              : "Background reference only. Never used as evidence or as a drafted fact."}
          </p>
        </div>
      ) : result.type === "llm_task" ? (
        <div className="p-5 sm:p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Instruction</p>
          <p className="mt-1 text-sm leading-6">{displayValue(result.result["instruction"])}</p>
          <p className="mt-5 whitespace-pre-wrap font-serif text-base leading-7">{displayValue(result.result["output"])}</p>
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <Badge variant="outline">{displayValue(result.result["model"])}</Badge>
            <Button variant="outline" size="sm" onClick={() => void navigator.clipboard.writeText(displayValue(result.result["output"]))}><Copy /> Copy</Button>
          </div>
        </div>
      ) : result.type === "private_note" ? (
        <div className="p-5 sm:p-8">
          <p className="whitespace-pre-wrap font-serif text-base leading-8">{longText}</p>
        </div>
      ) : result.type === "time_entry" ? (
        <div className="grid gap-4 p-5 sm:grid-cols-3 sm:p-6">
          <div><p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Hours</p><p className="mt-1 font-serif text-2xl">{displayValue(result.result["duration_hours"])}</p></div>
          <div><p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Matter</p><p className="mt-1 text-sm">{displayValue(result.result["matter_name"])}</p></div>
          <div><p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Billable</p><p className="mt-1 text-sm">{displayValue(result.result["billable"] ?? true)}</p></div>
          <div className="sm:col-span-3"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Narrative</p><p className="mt-2 whitespace-pre-wrap font-serif text-base leading-7">{longText}</p></div>
        </div>
      ) : (
        <div className="grid gap-x-8 gap-y-4 p-5 sm:grid-cols-2 sm:p-6">
          {Object.entries(result.result).filter(([key]) => !hiddenResultKeys.has(key)).map(([key, value]) => (
            <div key={key}>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">{key.replaceAll("_", " ")}</p>
              <p className="mt-1 whitespace-pre-wrap text-sm leading-6">{displayValue(value)}</p>
            </div>
          ))}
          {longText && result.type === "calendar_event" && (
            <div className="sm:col-span-2">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Description</p>
              <p className="mt-2 whitespace-pre-wrap font-serif text-base leading-7">{longText}</p>
            </div>
          )}
          <div className="flex flex-wrap gap-2 sm:col-span-2">
            {calendarHref && <Button asChild variant="outline"><a href={calendarHref} download="hakiscribe-event.ics"><Download /> Download .ics</a></Button>}
            <Button asChild variant="outline"><a href={shareUrl} target="_blank" rel="noreferrer"><MessageCircle /> WhatsApp</a></Button>
            {workspaceUrl && <Button asChild variant="outline"><a href={workspaceUrl} target="_blank" rel="noreferrer">Open in Ambiguous</a></Button>}
          </div>
        </div>
      )}
      <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-4 py-3 text-xs text-muted-foreground sm:px-6">
        <span>
          {Object.keys(result.result).some((key) => ["document_id", "ambiguous_document_id", "calendar_id", "ambiguous_event_id", "contact_id", "matter_id", "workspace_url"].includes(key))
            ? "Saved to the Session Library and connected tools"
            : "Saved as a local HakiScribe result"}
        </span>
        {result.type !== "draft_document" && result.type !== "calendar_event" && result.type !== "workspace_matter" && result.type !== "crm_entry" && (
          <Button asChild variant="ghost" size="sm" className="h-7 px-2 text-xs">
            <a href={shareUrl} target="_blank" rel="noreferrer"><MessageCircle className="size-3.5" /> WhatsApp</a>
          </Button>
        )}
      </footer>
    </article>
  );
}