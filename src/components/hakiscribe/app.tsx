import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
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
  Headphones,
  LockKeyhole,
  Mic,
  NotebookPen,
  Radio,
  RefreshCw,
  ShieldCheck,
  Square,
  UnlockKeyhole,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ComponentType } from "react";
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
  type DetectedAction,
  type FlaggedMoment,
  type Session,
  type SessionDetail,
  type SessionSource,
  type TranscriptSegment,
  displayValue,
  formatDuration,
  hakiApi,
  hasApiConfiguration,
  websocketUrl,
} from "@/lib/hakiscribe";
import { Brand, TrustLine } from "./brand";

const actionIcons: Record<ActionType, ComponentType<{ className?: string }>> = {
  draft_document: FileText,
  calendar_event: CalendarDays,
  workspace_matter: BriefcaseBusiness,
  crm_entry: ContactRound,
  private_note: NotebookPen,
  time_entry: Clock3,
};

function PageShell({ children, back }: { children: React.ReactNode; back?: boolean }) {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/90">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          {back ? (
            <Link to="/" className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground">
              <ArrowLeft className="size-4" /> Sessions
            </Link>
          ) : <Brand />}
          {back && <Brand compact />}
          <div className="hidden items-center gap-2 text-xs text-muted-foreground sm:flex">
            <ShieldCheck className="size-4 text-primary" /> Secure legal workspace
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}

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
  const [source, setSource] = useState<SessionSource>("mic");
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("code-switch");
  const sessions = useQuery({
    queryKey: ["sessions"],
    queryFn: hakiApi.listSessions,
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

  return (
    <PageShell>
      <main>
        <section className="border-b border-border bg-card">
          <div className="mx-auto grid min-h-[510px] max-w-6xl items-center gap-12 px-4 py-14 sm:px-6 lg:grid-cols-[1fr_24rem] lg:py-20">
            <div className="max-w-2xl">
              <p className="mb-4 text-sm font-semibold uppercase text-primary">Conversation to legal work</p>
              <h1 className="font-serif text-4xl font-semibold leading-tight text-foreground sm:text-6xl">
                Capture what matters. Leave with work ready.
              </h1>
              <p className="mt-5 max-w-xl text-base leading-7 text-muted-foreground sm:text-lg">
                Record a meeting or proceeding, verify the record, then choose the documents, follow-ups, matters, and entries HakiScribe prepares.
              </p>
              <TrustLine className="mt-7" />
            </div>

            <div className="border border-border bg-background p-5 sm:p-6">
              <h2 className="font-serif text-2xl font-semibold">Start a session</h2>
              <p className="mt-1 text-sm text-muted-foreground">No document choice needed. HakiScribe listens first.</p>
              <label className="mt-6 block text-xs font-semibold uppercase text-muted-foreground" htmlFor="session-title">Session title</label>
              <Input id="session-title" className="mt-2 h-11 bg-card" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Wanjiku client meeting" />
              <div className="mt-5 grid grid-cols-2 gap-1 rounded-md bg-muted p-1" aria-label="Recording source">
                {(["mic", "omi"] as const).map((item) => {
                  const Icon = item === "mic" ? Mic : Headphones;
                  return <Button key={item} type="button" variant={source === item ? "default" : "ghost"} className="h-10 shadow-none" onClick={() => setSource(item)}><Icon />{item === "mic" ? "Microphone" : "Omi wearable"}</Button>;
                })}
              </div>
              <label className="mt-5 block text-xs font-semibold uppercase text-muted-foreground" htmlFor="language">Language</label>
              <select id="language" value={language} onChange={(event) => setLanguage(event.target.value)} className="mt-2 h-11 w-full rounded-md border border-input bg-card px-3 text-sm outline-none focus:ring-1 focus:ring-ring">
                <option value="code-switch">English + Kiswahili</option>
                <option value="en">English</option>
                <option value="sw">Kiswahili</option>
              </select>
              <Button variant="warm" size="lg" className="mt-6 h-14 w-full text-base" onClick={() => create.mutate()} disabled={create.isPending || !hasApiConfiguration}>
                <span className="size-3 rounded-full bg-action-foreground" /> {create.isPending ? "Opening session…" : source === "mic" ? "Start recording" : "Start listening via Omi"}
              </Button>
              {create.error && <p className="mt-3 text-sm text-destructive">{create.error.message}</p>}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
          <div className="mb-6 flex items-end justify-between">
            <div><p className="text-xs font-semibold uppercase text-primary">Workspace</p><h2 className="mt-1 font-serif text-3xl font-semibold">Past sessions</h2></div>
            {sessions.data && <span className="text-sm text-muted-foreground">{sessions.data.length} total</span>}
          </div>
          {!hasApiConfiguration && <ConnectionError message="Add VITE_API_BASE_URL to connect the HakiScribe frontend to the FastAPI service." />}
          {sessions.error && <ConnectionError message={sessions.error.message} retry={() => void sessions.refetch()} />}
          {sessions.isLoading && <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-20 animate-pulse border border-border bg-card" />)}</div>}
          {sessions.data?.length === 0 && <div className="border-y border-border py-12 text-center text-muted-foreground">Your completed conversations will appear here.</div>}
          <div className="divide-y divide-border border-y border-border">
            {sessions.data?.map((session) => <SessionRow key={session.id} session={session} />)}
          </div>
        </section>
      </main>
    </PageShell>
  );
}

function SessionRow({ session }: { session: Session }) {
  const Icon = session.source === "mic" ? Mic : Headphones;
  return (
    <Link to="/sessions/$sessionId" params={{ sessionId: session.id }} search={{ fresh: false }} className="grid grid-cols-[auto_1fr_auto] items-center gap-4 bg-background py-4 transition-colors hover:bg-card sm:px-3">
      <span className="grid size-10 place-items-center rounded-md border border-border bg-card text-primary"><Icon className="size-4" /></span>
      <span className="min-w-0"><span className="block truncate font-medium text-foreground">{session.title}</span><span className="mt-1 block text-xs text-muted-foreground">{new Date(session.created_at).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })} · {session.source === "omi" ? "Omi wearable" : "Microphone"}</span></span>
      <Badge variant={session.status === "exported" ? "default" : "outline"} className="capitalize">{session.status}</Badge>
    </Link>
  );
}

type FlowStep = "recording" | "speakers" | "redact" | "analyzing" | "tray" | "results";

export function SessionPage({ sessionId, fresh }: { sessionId: string; fresh: boolean }) {
  const detail = useQuery({ queryKey: ["session", sessionId], queryFn: () => hakiApi.getSession(sessionId), retry: false });
  const [step, setStep] = useState<FlowStep | null>(null);
  useEffect(() => {
    if (!detail.data || step) return;
    if (fresh && detail.data.status === "recording") setStep("recording");
    else if (detail.data.detected_actions?.length) setStep("tray");
    else if (detail.data.status === "recording") setStep("recording");
    else setStep("analyzing");
  }, [detail.data, fresh, step]);

  if (detail.isLoading || !step) return <PageShell back><main className="mx-auto max-w-4xl px-4 py-20"><div className="h-1 w-full animate-reading-line bg-primary" /><p className="mt-5 text-center text-muted-foreground">Opening secure session…</p></main></PageShell>;
  if (detail.error || !detail.data) return <PageShell back><main className="mx-auto max-w-3xl px-4 py-16"><ConnectionError message={detail.error?.message ?? "Session not found"} retry={() => void detail.refetch()} /></main></PageShell>;

  const session = detail.data;
  const replaceDetail = (next: SessionDetail) => detail.refetch().then(() => next);
  if (step === "recording") return <RecordingScreen session={session} onStopped={(next) => { void replaceDetail(next); setStep("speakers"); }} />;
  if (step === "speakers") return <SpeakerScreen session={session} onNext={() => { void detail.refetch(); setStep("redact"); }} />;
  if (step === "redact") return <RedactScreen session={session} onNext={() => setStep("analyzing")} />;
  if (step === "analyzing") return <AnalyzingScreen sessionId={session.id} onComplete={() => { void detail.refetch(); setStep("tray"); }} />;
  return <PageShell back><ActionWorkspace session={session} initialResults={session.action_results ?? []} showResults={step === "results"} onResults={() => setStep("results")} /></PageShell>;
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
          nextRecorder.start(2500);
        };
      }).catch(() => setError("Microphone access is required for a Mic session. Allow access, then reopen this session."));
    }
    return () => {
      window.clearInterval(timer);
      stopping.current = true;
      if (recorder.current?.state === "recording") recorder.current.stop();
      socket.current?.close();
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, [session.id, session.source]);

  const flag = async () => {
    try {
      const moment = await hakiApi.flagMoment(session.id, { at_ms: elapsed });
      setFlags((current) => [...current, moment]);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "The moment could not be flagged."); }
  };
  const stop = async () => {
    setStoppingNow(true); stopping.current = true;
    if (recorder.current?.state === "recording") recorder.current.stop();
    socket.current?.close(); stream.current?.getTracks().forEach((track) => track.stop());
    try { onStopped(await hakiApi.getSession(session.id)); } catch (caught) { setError(caught instanceof Error ? caught.message : "The session could not be loaded."); setStoppingNow(false); }
  };

  return (
    <div className="flex min-h-screen flex-col bg-primary text-primary-foreground">
      <header className="flex items-center justify-between border-b border-primary-foreground/15 px-4 py-4 sm:px-8"><Brand compact /><span className="inline-flex items-center gap-2 text-xs"><span className="size-2 animate-pulse rounded-full bg-action" /> Recording</span></header>
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-8 sm:px-8">
        <div className="text-center"><p className="text-sm text-primary-foreground/65">{session.title}</p><p className="mt-3 font-mono text-5xl tabular-nums sm:text-6xl">{formatDuration(elapsed)}</p></div>
        <div className="mt-7 flex min-h-8 gap-2 overflow-x-auto pb-2">
          {flags.map((item) => <span key={item.id} className="shrink-0 rounded-md border border-primary-foreground/20 bg-primary-foreground/10 px-3 py-1.5 text-xs">{formatDuration(item.at_ms)} · {item.label ?? "Flagged moment"}</span>)}
        </div>
        <div className="my-8 flex h-24 items-center justify-center gap-1" aria-label="Live audio waveform">
          {Array.from({ length: 28 }, (_, index) => <span key={index} className="h-16 w-1 rounded-full bg-primary-foreground/70 animate-waveform" style={{ animationDelay: `${(index % 8) * 90}ms` }} />)}
        </div>
        <Button variant="warm" className="mx-auto h-24 w-full max-w-md text-xl" onClick={() => void flag()}><Flag className="size-7" /> Flag this moment</Button>
        <div className="mt-8 min-h-24 border-t border-primary-foreground/15 pt-5">
          {session.source === "omi" ? <p className="flex items-center justify-center gap-2 text-sm text-primary-foreground/70"><Radio className="size-4" /> Listening via Omi. Transcript segments arrive securely from your wearable.</p> : <div className="max-h-28 space-y-2 overflow-y-auto text-sm italic text-primary-foreground/55">{captions.slice(-4).map((line) => <p key={line.id}><span className="font-semibold not-italic">{line.speaker ?? "Speaker"}:</span> {line.text}</p>)}{!captions.length && <p className="text-center">Live captions will appear here as people speak.</p>}</div>}
        </div>
        {error && <p className="mt-4 text-center text-sm text-primary-foreground">{error}</p>}
        <div className="mt-auto flex flex-col items-center pt-8"><Button variant="quiet" className="h-12 min-w-36 border-primary-foreground/25 bg-primary-foreground/10 text-primary-foreground hover:bg-primary-foreground/20" onClick={() => void stop()} disabled={stoppingNow}><Square className="fill-current" /> {stoppingNow ? "Stopping…" : "Stop"}</Button><TrustLine className="mt-5 text-primary-foreground/65 [&_svg]:text-primary-foreground" /></div>
      </main>
    </div>
  );
}

function FlowHeader({ step, title, copy }: { step: string; title: string; copy: string }) {
  return <div className="mb-8"><p className="text-xs font-semibold uppercase text-primary">{step}</p><h1 className="mt-2 font-serif text-3xl font-semibold sm:text-4xl">{title}</h1><p className="mt-3 max-w-2xl leading-7 text-muted-foreground">{copy}</p></div>;
}

function SpeakerScreen({ session, onNext }: { session: SessionDetail; onNext: () => void }) {
  const speakers = useMemo(() => Array.from(new Set(session.transcript.map((s) => s.speaker).filter((s): s is string => Boolean(s)))), [session.transcript]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const mutation = useMutation({ mutationFn: () => hakiApi.updateSpeakers(session.id, mapping), onSuccess: onNext });
  return <PageShell back><main className="mx-auto max-w-3xl px-4 py-12 sm:px-6"><FlowHeader step="Step 1 of 2" title="Who was speaking?" copy="Names entered here flow into legal documents. Review them deliberately, or keep the original labels." />
    <div className="divide-y divide-border border-y border-border bg-card">{speakers.map((speaker) => <div key={speaker} className="grid gap-2 py-5 sm:grid-cols-[10rem_1fr] sm:items-center sm:px-4"><label className="text-sm font-semibold" htmlFor={`speaker-${speaker}`}>{speaker}</label><Input id={`speaker-${speaker}`} className="h-11" placeholder="Type their real name" value={mapping[speaker] ?? ""} onChange={(event) => setMapping((current) => ({ ...current, [speaker]: event.target.value }))} /></div>)}</div>
    {!speakers.length && <p className="border-y border-border py-8 text-center text-muted-foreground">No speaker labels were found. You can continue to the transcript check.</p>}
    {mutation.error && <p className="mt-4 text-sm text-destructive">{mutation.error.message}</p>}
    <div className="mt-8 flex justify-end gap-3"><Button variant="ghost" onClick={onNext}>Skip</Button><Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !Object.values(mapping).some((name) => name.trim())}>{mutation.isPending ? "Saving…" : "Save names"}</Button></div>
  </main></PageShell>;
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
  return <PageShell back><main className="mx-auto max-w-4xl px-4 py-12 sm:px-6"><FlowHeader step="Step 2 of 2" title="Protect what stays private" copy="Lock any privileged or off-record line. It stays visible to you, but will not be sent for analysis." />
    {error && <ConnectionError message={error} />}
    <div className="mt-6 divide-y divide-border border-y border-border bg-card">{segments.map((segment) => <div key={segment.id} className={cn("grid grid-cols-[1fr_auto] gap-4 px-3 py-4 sm:px-5", segment.redacted && "bg-privileged/70 text-muted-foreground")}><div><div className="mb-1 flex flex-wrap items-center gap-2"><span className="text-xs font-semibold text-primary">{segment.speaker ?? "Speaker"}</span><span className="font-mono text-[11px] text-muted-foreground">{formatDuration(segment.start_ms)}</span>{segment.redacted && <Badge variant="outline" className="border-privileged-foreground/30 text-privileged-foreground">Won't be used</Badge>}</div><p className={cn("font-serif text-base leading-7", segment.redacted && "line-through decoration-privileged-foreground/50")}>{segment.text}</p></div><Button variant="ghost" size="icon" aria-label={segment.redacted ? "Include this line" : "Mark privileged"} title={segment.redacted ? "Include this line" : "Mark privileged"} onClick={() => void toggle(segment)}>{segment.redacted ? <LockKeyhole className="text-privileged-foreground" /> : <UnlockKeyhole />}</Button></div>)}</div>
    {!segments.length && <p className="py-10 text-center text-muted-foreground">No transcript segments have arrived yet. You can still continue and analyze the available session data.</p>}
    <div className="sticky bottom-0 mt-6 border-t border-border bg-background/95 py-4 text-right"><Button size="lg" onClick={() => void continueFlow()}>Continue to analysis</Button></div>
  </main></PageShell>;
}

function AnalyzingScreen({ sessionId, onComplete }: { sessionId: string; onComplete: () => void }) {
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    void hakiApi.finalize(sessionId).then(() => hakiApi.detect(sessionId)).then(() => { if (active) onComplete(); }).catch((caught) => { if (active) setError(caught instanceof Error ? caught.message : "Analysis could not be completed."); });
    return () => { active = false; };
  }, [sessionId, onComplete]);
  return <PageShell back><main className="mx-auto flex min-h-[70vh] max-w-xl flex-col items-center justify-center px-5 text-center"><div className="w-40 space-y-2" aria-hidden>{[0,1,2,3].map((item) => <div key={item} className="h-1 origin-left animate-reading-line bg-primary" style={{ animationDelay: `${item * 220}ms` }} />)}</div><h1 className="mt-10 font-serif text-3xl font-semibold">Reviewing what happened…</h1><p className="mt-3 leading-7 text-muted-foreground">Checking the verified record for documents, dates, matters, contacts, notes, and billable work.</p><p className="mt-5 text-xs text-muted-foreground">OpenAI/OpenRouter analysis · Trigger.dev durable processing</p>{error && <div className="mt-8 w-full"><ConnectionError message={error} retry={() => window.location.reload()} /></div>}</main></PageShell>;
}

function ActionWorkspace({ session, initialResults, showResults, onResults }: { session: SessionDetail; initialResults: ActionResult[]; showResults: boolean; onResults: () => void }) {
  const [selected, setSelected] = useState(() => new Set(session.detected_actions.filter((action) => action.pre_checked).map((action) => action.id)));
  const [actions, setActions] = useState(session.detected_actions);
  const [results, setResults] = useState(initialResults);
  const generate = useMutation({ mutationFn: () => hakiApi.generate(session.id, Array.from(selected)), onSuccess: (data) => { setResults(data); onResults(); } });
  const select = (id: string, checked: boolean) => setSelected((current) => { const next = new Set(current); checked ? next.add(id) : next.delete(id); return next; });
  return <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
    <div className="flex flex-col justify-between gap-5 border-b border-border pb-7 sm:flex-row sm:items-end"><div><p className="text-xs font-semibold uppercase text-primary">{showResults ? "Generated work" : "Action tray"}</p><h1 className="mt-2 font-serif text-3xl font-semibold sm:text-4xl">{session.title}</h1><p className="mt-2 text-sm text-muted-foreground">{showResults ? "Review and edit before anything leaves your workspace." : `${actions.length} possible legal actions, each grounded in the transcript.`}</p></div><TrustLine /></div>
    <div className="mt-6 flex gap-2 border-b border-border"><Button variant={!showResults ? "ghost" : "link"} onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>Detected actions</Button>{results.length > 0 && <Button variant={showResults ? "ghost" : "link"} onClick={onResults}>Results ({results.length})</Button>}</div>
    {showResults && results.length ? <ResultsList results={results} /> : <>
      <div className="my-6 flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-muted-foreground">Review, edit, then choose what HakiScribe should produce.</p><Button variant="outline" size="sm" onClick={() => setSelected(new Set(actions.filter((action) => action.pre_checked).map((action) => action.id)))}><Check /> Select high-confidence</Button></div>
      <div className="space-y-3">{actions.map((action) => <ActionCard key={action.id} action={action} transcript={session.transcript} checked={selected.has(action.id)} onChecked={(checked) => select(action.id, checked)} onFields={(fields) => setActions((current) => current.map((item) => item.id === action.id ? { ...item, extracted_fields: fields } : item))} />)}</div>
      {!actions.length && <div className="border-y border-border py-12 text-center"><h2 className="font-serif text-2xl">No actions detected</h2><p className="mt-2 text-muted-foreground">The verified transcript did not contain enough information to propose legal work.</p></div>}
      {generate.error && <div className="mt-5"><ConnectionError message={generate.error.message} /></div>}
      <div className="sticky bottom-0 mt-8 border-t border-border bg-background/95 py-4"><Button variant="warm" size="lg" className="h-12 w-full" disabled={!selected.size || generate.isPending} onClick={() => generate.mutate()}>{generate.isPending ? "Generating selected work…" : `Generate selected (${selected.size})`}</Button></div>
    </>}
  </main>;
}

function ActionCard({ action, transcript, checked, onChecked, onFields }: { action: DetectedAction; transcript: TranscriptSegment[]; checked: boolean; onChecked: (checked: boolean) => void; onFields: (fields: Record<string, unknown>) => void }) {
  const [open, setOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(false);
  const Icon = actionIcons[action.type];
  const source = transcript.find((segment) => segment.id === action.source_segment_id);
  const speculative = !action.pre_checked || action.confidence < 0.7;
  return <article className={cn("border bg-card transition-colors", checked ? "border-primary" : "border-border", speculative && !checked && "opacity-65")}>
    <div className="grid grid-cols-[auto_1fr_auto] gap-3 p-4 sm:p-5"><span className="grid size-10 place-items-center rounded-md bg-secondary text-secondary-foreground"><Icon className="size-5" /></span><button type="button" className="min-w-0 text-left" onClick={() => setOpen(!open)}><h2 className="font-semibold text-foreground">{action.title}</h2><p className="mt-1 text-sm leading-6 text-muted-foreground">{action.preview}</p></button><Checkbox checked={checked} onCheckedChange={(value) => onChecked(value === true)} aria-label={`Select ${action.title}`} className="mt-2 size-5" /></div>
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3 text-xs sm:px-5"><div className="flex items-center gap-2"><Badge variant={speculative ? "outline" : "secondary"}>{action.confidence_reason ?? `${Math.round(action.confidence * 100)}% confidence`}</Badge>{action.extracted_fields.background_info !== undefined && <Badge variant="outline">Exa context</Badge>}</div><div className="flex items-center gap-3">{source && <button type="button" className="font-semibold text-primary hover:underline" onClick={() => setSourceOpen(!sourceOpen)}>View source</button>}<button type="button" aria-label={open ? "Collapse action" : "Edit action"} onClick={() => setOpen(!open)}><ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} /></button></div></div>
    {sourceOpen && source && <div className="border-t border-border bg-secondary/35 px-4 py-4 sm:px-5"><p className="mb-1 text-xs font-semibold text-primary">{source.speaker ?? "Speaker"} · {formatDuration(source.start_ms)}</p><blockquote className="font-serif leading-7">“{source.text}”</blockquote></div>}
    {open && <div className="grid gap-4 border-t border-border p-4 sm:grid-cols-2 sm:p-5">{Object.entries(action.extracted_fields).map(([key, value]) => <label key={key} className={cn("text-xs font-semibold capitalize text-muted-foreground", typeof value === "object" && "sm:col-span-2")}>{key.replaceAll("_", " ")} {typeof value === "object" ? <Textarea className="mt-2 min-h-24 bg-background font-mono text-xs" value={displayValue(value)} onChange={(event) => onFields({ ...action.extracted_fields, [key]: event.target.value })} /> : <Input className="mt-2 bg-background text-foreground" value={displayValue(value)} onChange={(event) => onFields({ ...action.extracted_fields, [key]: event.target.value })} />}</label>)}</div>}
  </article>;
}

function ResultsList({ results }: { results: ActionResult[] }) {
  return <div className="mt-8 space-y-4">{results.map((item) => <ResultCard key={item.action_id} result={item} />)}</div>;
}

function ResultCard({ result }: { result: ActionResult }) {
  const Icon = actionIcons[result.type];
  const [documentText, setDocumentText] = useState(displayValue(result.result.document_text ?? ""));
  if (result.status === "error") return <article className="border border-destructive/30 bg-card p-5"><div className="flex items-center gap-3"><AlertCircle className="size-5 text-destructive" /><div><h2 className="font-semibold">This item was not generated</h2><p className="mt-1 text-sm text-muted-foreground">{result.error ?? "The service returned an error for this item."}</p></div></div></article>;
  const calendarHref = typeof result.result.ics === "string" ? `data:text/calendar;charset=utf-8,${encodeURIComponent(result.result.ics)}` : null;
  return <article className="border border-border bg-card"><header className="flex items-center gap-3 border-b border-border px-4 py-4 sm:px-6"><span className="grid size-9 place-items-center rounded-md bg-success text-success-foreground"><Icon className="size-4" /></span><div><p className="text-xs font-semibold uppercase text-success-foreground">Generated</p><h2 className="font-semibold capitalize">{result.type.replaceAll("_", " ")}</h2></div></header>
    {result.type === "draft_document" ? <div className="p-4 sm:p-8"><div className="mb-3 flex justify-end gap-2"><Button variant="outline" size="sm" onClick={() => void navigator.clipboard.writeText(documentText)}><Copy /> Copy</Button></div><Textarea aria-label="Editable legal document" value={documentText} onChange={(event) => setDocumentText(event.target.value)} className="min-h-[28rem] resize-y border-0 bg-background p-6 font-serif text-base leading-8 shadow-none focus-visible:ring-1 sm:p-10" /></div> : <div className="grid gap-x-8 gap-y-4 p-5 sm:grid-cols-2 sm:p-6">{Object.entries(result.result).filter(([key]) => key !== "ics").map(([key, value]) => <div key={key}><p className="text-xs font-semibold uppercase text-muted-foreground">{key.replaceAll("_", " ")}</p><p className="mt-1 whitespace-pre-wrap text-sm leading-6">{displayValue(value)}</p></div>)}{calendarHref && <div className="sm:col-span-2"><Button asChild variant="outline"><a href={calendarHref} download="hakiscribe-event.ics"><Download /> Download .ics</a></Button></div>}</div>}
    <footer className="border-t border-border px-4 py-3 text-xs text-muted-foreground sm:px-6">{Object.keys(result.result).some((key) => ["document_id", "calendar_id", "contact_id", "matter_id"].includes(key)) ? "Delivered through connected HakiChain tools" : "Saved as a local HakiScribe result"}</footer>
  </article>;
}