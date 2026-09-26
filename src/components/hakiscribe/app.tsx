import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BriefcaseBusiness,
  CalendarDays,
  Check,
  ChevronDown,
  Clock3,
  CalendarPlus,
  Cloud,
  ContactRound,
  Copy,
  Download,
  ExternalLink,
  FileText,
  Flag,
  Globe,
  Headphones,
  BookOpen,
  LockKeyhole,
  MessageCircle,
  MessageSquare,
  Mic,
  NotebookPen,
  Radio,
  RefreshCw,
  Scale,
  Search,
  ShieldCheck,
  Sparkles,
  Square,
  UnlockKeyhole,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ComponentType, ReactNode } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  type CarouselApi,
} from "@/components/ui/carousel";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  ApiError,
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
  DEMO_CREDENTIALS_QUERY_KEY,
  displayValue,
  downloadTextFile,
  formatBillableHours,
  formatDuration,
  friendlyErrorMessage,
  reauthProvider,
  friendlyModelName,
  friendlyStatusNote,
  hakiApi,
  hasApiConfiguration,
  humanizeFieldLabel,
  isPayloadOnlyFieldKey,
  isReferenceFieldKey,
  omiWebhookUrl,
  parseBackgroundInfo,
  shouldShowReferenceField,
  shouldShowResultField,
  sourceHostname,
  warmWorkspace,
  whatsappShareUrl,
  websocketUrl,
} from "@/lib/hakiscribe";
import {
  LANGUAGE_OPTIONS,
  languageLabel,
  loadWorkspaceSettings,
  shouldAutoSaharaRefine,
  usesSaharaRefine,
} from "@/lib/workspace-settings";
import { useDemoMode } from "@/hooks/use-demo-mode";
import { filterDemoContacts, filterDemoMatters, filterDemoSessions } from "@/lib/demo-mode";
import { detectLanguageMix, detectedModeLabel } from "@/lib/language-detect";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import legalRoomImage from "@/assets/hakiscribe-legal-room.jpg";
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
  {
    n: "01",
    title: "Listen first",
    copy: "Mic or Omi Wearables. Flag what matters without looking down.",
  },
  {
    n: "02",
    title: "Verify the record",
    copy: "Name speakers. Lock privileged lines before any model sees them.",
  },
  {
    n: "03",
    title: "Choose the work",
    copy: "Letters, dates, matters, contacts, notes, and time — each sourced.",
  },
];

const environments = [
  {
    place: "In the room",
    title: "Mic or Omi Wearables",
    copy: "The agent listens where the conversation happens. Flag a date or admission without breaking eye contact.",
  },
  {
    place: "In the pocket",
    title: "WhatsApp handoff",
    copy: "Kenyan practice already lives in WhatsApp. Share an editable draft for review never auto-sent as legal advice.",
  },
  {
    place: "At the desk",
    title: "Docs, calendar, legal intelligence",
    copy: "Chosen work lands in Ambiguous. Exa retrieves authorities only when they connect to the matter or the verified transcript.",
  },
];

const lawyerPersonas = [
  {
    icon: BriefcaseBusiness,
    role: "Advocates",
    title: "Leave the client meeting with the next document begun",
    copy: "Capture intakes and strategy calls across African languages and English code-switch. Flag dates and admissions, lock privilege, then choose letters, matters, contacts, and billable time from the Action Tray.",
  },
  {
    icon: Scale,
    role: "Judges",
    title: "Turn spoken proceedings into a usable record",
    copy: "Record mentions and hearings without rewriting every line by hand. Verify speakers, protect off-record moments, and leave with structured notes ready for chambers review.",
  },
  {
    icon: NotebookPen,
    role: "Legal clerks",
    title: "Keep follow-ups, filings, and diaries current",
    copy: "After a meeting or court day, generate calendar events, private notes, and matter updates grounded in the transcript — so nothing important waits on memory alone.",
  },
  {
    icon: ContactRound,
    role: "Pupils",
    title: "Learn from the room without losing the detail",
    copy: "Sit in with seniors and leave with speaker-named notes, research prompts, and source-traced drafts you can edit — a cleaner path from observation to usable work product.",
  },
  {
    icon: Clock3,
    role: "Practice managers",
    title: "See work leave the room, not just the recording",
    copy: "Matters, CRM updates, and time entries stay linked to verified conversations. The firm gets a clearer trail from spoken work to desk work, without exposing cases on a public page.",
  },
];

function ConnectionError({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <Alert variant="destructive" className="border-destructive/30 bg-card">
      <AlertCircle />
      <AlertTitle>Connection unavailable</AlertTitle>
      <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
        <span>{friendlyErrorMessage(message)}</span>
        {retry && (
          <Button variant="outline" size="sm" onClick={retry}>
            <RefreshCw /> Try again
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
}

function PersonasCarousel() {
  const [api, setApi] = useState<CarouselApi>();
  const [selected, setSelected] = useState(0);
  const [canScrollPrev, setCanScrollPrev] = useState(false);
  const [canScrollNext, setCanScrollNext] = useState(false);

  useEffect(() => {
    if (!api) return;
    const onSelect = () => {
      setSelected(api.selectedScrollSnap());
      setCanScrollPrev(api.canScrollPrev());
      setCanScrollNext(api.canScrollNext());
    };
    onSelect();
    api.on("select", onSelect);
    api.on("reInit", onSelect);
    return () => {
      api.off("select", onSelect);
      api.off("reInit", onSelect);
    };
  }, [api]);

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:mb-8 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Legal roles">
          {lawyerPersonas.map((persona, index) => {
            const active = selected === index;
            return (
              <button
                key={persona.role}
                type="button"
                role="tab"
                aria-selected={active}
                className={cn(
                  "min-h-10 rounded-full border px-3.5 py-2 text-sm font-medium transition-colors",
                  active
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground",
                )}
                onClick={() => api?.scrollTo(index)}
              >
                {persona.role}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2 self-end sm:self-auto">
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="size-10 rounded-full"
            aria-label="Previous role"
            disabled={!canScrollPrev}
            onClick={() => api?.scrollPrev()}
          >
            <ArrowLeft className="size-4" />
          </Button>
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="size-10 rounded-full"
            aria-label="Next role"
            disabled={!canScrollNext}
            onClick={() => api?.scrollNext()}
          >
            <ArrowRight className="size-4" />
          </Button>
        </div>
      </div>

      <Carousel
        setApi={setApi}
        opts={{ align: "start", loop: false, skipSnaps: false, dragFree: false }}
        className="w-full"
      >
        <CarouselContent className="-ml-3 sm:-ml-4">
          {lawyerPersonas.map(({ icon: Icon, role, title, copy }, index) => (
            <CarouselItem
              key={role}
              className="basis-[88%] pl-3 sm:basis-[70%] sm:pl-4 md:basis-[48%] lg:basis-[42%]"
            >
              <article
                className={cn(
                  "chamber-card flex h-full min-h-[18.5rem] flex-col rounded-2xl border p-6 transition-colors sm:min-h-[20rem] sm:p-7",
                  selected === index ? "border-primary bg-secondary/25" : "border-border bg-card",
                )}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="grid size-11 place-items-center rounded-xl bg-secondary text-primary">
                      <Icon className="size-5" />
                    </span>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
                      {role}
                    </p>
                  </div>
                  <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
                    {String(index + 1).padStart(2, "0")} /{" "}
                    {String(lawyerPersonas.length).padStart(2, "0")}
                  </span>
                </div>
                <h3 className="mt-6 font-serif text-2xl font-semibold leading-snug tracking-tight">
                  {title}
                </h3>
                <p className="mt-4 flex-1 text-sm leading-7 text-muted-foreground">{copy}</p>
              </article>
            </CarouselItem>
          ))}
        </CarouselContent>
      </Carousel>

      <div className="mt-5 flex items-center justify-center gap-2" aria-hidden>
        {lawyerPersonas.map((persona, index) => (
          <button
            key={persona.role}
            type="button"
            aria-label={`Show ${persona.role}`}
            className={cn(
              "h-1.5 rounded-full transition-all",
              selected === index
                ? "w-7 bg-primary"
                : "w-1.5 bg-border hover:bg-muted-foreground/40",
            )}
            onClick={() => api?.scrollTo(index)}
          />
        ))}
      </div>

      <div className="mt-10 flex flex-col gap-4 rounded-2xl border border-border bg-card/70 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div className="min-w-0">
          <p className="font-serif text-xl font-semibold">
            Start where the conversation already is.
          </p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Open a private workspace to record, verify privilege, and choose the work.
          </p>
        </div>
        <Button asChild className="w-full shrink-0 sm:w-auto">
          <Link to="/new">Enter private workspace</Link>
        </Button>
      </div>
    </div>
  );
}

export function LandingPage() {
  const queryClient = useQueryClient();
  const featureGroups = [
    {
      icon: Mic,
      title: "Capture without disruption",
      copy: "Record by microphone or Omi while hands-free flags preserve dates, admissions, and commitments in the moment.",
    },
    {
      icon: LockKeyhole,
      title: "Privilege before processing",
      copy: "Relabel speakers and lock privileged or off-record lines before detection. Hidden lines stay reversible and outside model context.",
    },
    {
      icon: FileText,
      title: "Work, not a transcript dump",
      copy: "Choose only the letters, notes, calendar entries, matters, contacts, time records, and research the conversation supports.",
    },
    {
      icon: ShieldCheck,
      title: "Every claim traceable",
      copy: "Each proposed action points back to its source line, so a reviewer can verify the record before anything leaves the workspace.",
    },
    {
      icon: Sparkles,
      title: "Your choice of intelligence",
      copy: "Use the built-in model or a connected provider for transcript-grounded tasks, with legal research and web context kept distinct from evidence.",
    },
    {
      icon: Cloud,
      title: "Connect the tools you use",
      copy: "Send approved work to document, calendar, storage, and practice systems through durable, server-side automations.",
    },
  ];

  useEffect(() => {
    if (!hasApiConfiguration) return;
    void queryClient.prefetchQuery({
      queryKey: DEMO_CREDENTIALS_QUERY_KEY,
      queryFn: hakiApi.demoCredentials,
      staleTime: 5 * 60_000,
    });
    void warmWorkspace();
  }, [queryClient]);

  return (
    <PageShell>
      <main>
        <section className="relative isolate min-h-[calc(100svh-7.25rem)] overflow-hidden border-b border-border bg-intelligence text-intelligence-foreground">
          <img
            src={legalRoomImage}
            alt="Kenyan legal professionals reviewing case papers around a conference table"
            width={1600}
            height={900}
            className="absolute inset-0 size-full object-cover object-[62%_center]"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-intelligence via-intelligence/95 to-intelligence/20" />
          <div className="relative mx-auto flex min-h-[calc(100svh-7.25rem)] max-w-6xl items-end px-4 pb-14 pt-20 sm:px-6 sm:pb-20 lg:items-center lg:pb-24">
            <div className="max-w-3xl animate-ink-rise">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-intelligence-accent">
                Conversation to legal work
              </p>
              <h1 className="mt-4 max-w-3xl font-serif text-4xl font-semibold leading-[1.08] sm:text-6xl lg:text-7xl">
                Capture what matters.{" "}
                <em className="italic text-intelligence-accent">
                  Leave with your Legal work ready.
                </em>
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-7 text-intelligence-muted sm:text-lg">
                HakiScribe is the private listening companion for legal rooms. Verify the record,
                protect privilege, then choose the source-traceable work it prepares.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Button asChild variant="warm" size="lg" className="h-13 px-6 text-base">
                  <Link to="/new">
                    <Mic /> Start a private session
                  </Link>
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="h-13 border-intelligence-border bg-intelligence/60 px-6 text-intelligence-foreground hover:bg-intelligence-panel hover:text-intelligence-foreground"
                >
                  <a href="#how-it-works">How it works</a>
                </Button>
              </div>
              <TrustLine className="mt-7 max-w-xl text-left text-intelligence-muted" />
            </div>
          </div>
        </section>

        <section id="how-it-works" className="border-b border-border bg-background">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
            <SectionEyebrow>From spoken record to reviewed action</SectionEyebrow>
            <div className="mt-3 grid gap-8 lg:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)] lg:gap-16">
              <h2 className="font-serif text-3xl font-semibold leading-tight sm:text-5xl">
                A disciplined path from the room to the work.
              </h2>
              <ol className="divide-y divide-border border-y border-border">
                {practiceSteps.map((step) => (
                  <li
                    key={step.n}
                    className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-4 py-5 sm:grid-cols-[3.5rem_minmax(0,1fr)] sm:py-6"
                  >
                    <span className="font-serif text-lg text-action">{step.n}</span>
                    <div>
                      <h3 className="font-semibold">{step.title}</h3>
                      <p className="mt-1 text-sm leading-6 text-muted-foreground">{step.copy}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section className="bg-card">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
            <SectionHeading
              eyebrow="Built for legal practice"
              title="The record stays central. The work moves forward."
            />
            <div className="grid border-l border-t border-border sm:grid-cols-2 lg:grid-cols-3">
              {featureGroups.map(({ icon: Icon, title, copy }) => (
                <article key={title} className="border-b border-r border-border p-5 sm:p-7">
                  <span className="grid size-10 place-items-center rounded-md bg-secondary text-primary">
                    <Icon className="size-5" />
                  </span>
                  <h3 className="mt-5 font-serif text-xl font-semibold">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{copy}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="border-y border-intelligence-border bg-intelligence text-intelligence-foreground">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-intelligence-accent">
              Where HakiScribe works
            </p>
            <div className="mt-8 grid gap-px overflow-hidden rounded-lg border border-intelligence-border bg-intelligence-border md:grid-cols-3">
              {environments.map((item) => (
                <article key={item.place} className="bg-intelligence p-6 sm:p-8">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-intelligence-accent">
                    {item.place}
                  </p>
                  <h3 className="mt-3 font-serif text-2xl font-semibold">{item.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-intelligence-muted">{item.copy}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-background">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
            <SectionHeading
              eyebrow="Who it helps"
              title="Built for the legal professionals who carry the record."
            />
            <p className="mb-8 max-w-2xl text-base leading-7 text-muted-foreground sm:mb-10">
              HakiScribe serves Kenyan legal rooms — advocates, benches, clerks, pupils, and
              practice desks — wherever spoken work still outruns paperwork.
            </p>
            <PersonasCarousel />
          </div>
        </section>
      </main>
      <WorkspaceFooter />
    </PageShell>
  );
}

export function NewSessionPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { enabled: demoDataEnabled } = useDemoMode();
  const [source, setSource] = useState<SessionSource>("mic");
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("code-switch");
  const [practiceName, setPracticeName] = useState("");
  useEffect(() => {
    const stored = loadWorkspaceSettings();
    setSource(stored.workspace.defaultSource);
    setLanguage(stored.workspace.defaultLanguage);
    setPracticeName(stored.profile.practiceName.trim());
  }, []);
  const sessions = useQuery({
    queryKey: ["sessions", { includeDemo: demoDataEnabled }],
    queryFn: () => hakiApi.listSessions({ includeDemo: demoDataEnabled }),
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
  const health = useQuery({
    queryKey: ["health"],
    queryFn: hakiApi.health,
    enabled: hasApiConfiguration,
    retry: false,
  });
  const intronLinked = Boolean(health.data?.integrations?.["intron"]);
  const wantsSaharaRefine = usesSaharaRefine(language);
  const create = useMutation({
    mutationFn: () =>
      hakiApi.createSession({
        title: title.trim() || `New ${source === "mic" ? "recording" : "Omi session"}`,
        source,
        ...(language ? { language_hint: language } : {}),
      }),
    onSuccess: (session) =>
      navigate({
        to: "/sessions/$sessionId",
        params: { sessionId: session.id },
        search: { fresh: true },
      }),
  });
  const showcase = useMutation({
    mutationFn: hakiApi.ensureShowcase,
    onSuccess: (session) => {
      void queryClient.invalidateQueries({ queryKey: ["sessions"] });
      void queryClient.invalidateQueries({ queryKey: ["matters"] });
      void queryClient.invalidateQueries({ queryKey: ["contacts"] });
      navigate({
        to: "/sessions/$sessionId",
        params: { sessionId: session.id },
        search: { fresh: false },
      });
    },
    onError: (error) => toast.error(friendlyErrorMessage(error)),
  });
  const saharaDemo = useMutation({
    mutationFn: hakiApi.ensureSaharaDemo,
    onSuccess: (session) => {
      void queryClient.invalidateQueries({ queryKey: ["sessions"] });
      void queryClient.invalidateQueries({ queryKey: ["matters"] });
      void queryClient.invalidateQueries({ queryKey: ["contacts"] });
      toast.success("Multilingual sessions added to the library");
      navigate({
        to: "/sessions/$sessionId",
        params: { sessionId: session.id },
        search: { fresh: false },
      });
    },
    onError: (error) => toast.error(friendlyErrorMessage(error)),
  });
  const syncLibrary = useMutation({
    mutationFn: hakiApi.syncDemoLibrary,
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["sessions"] });
      void queryClient.invalidateQueries({ queryKey: ["matters"] });
      void queryClient.invalidateQueries({ queryKey: ["contacts"] });
      if (result.created > 0)
        toast.success(
          result.completing ? "Library restored. Finishing the trays." : "Library restored.",
        );
      if (result.completing)
        window.setTimeout(() => {
          void queryClient.invalidateQueries({ queryKey: ["sessions"] });
          void queryClient.invalidateQueries({ queryKey: ["matters"] });
        }, 12000);
    },
    onError: (error) => {
      if (!(error instanceof ApiError && error.status === 404))
        toast.error(friendlyErrorMessage(error));
    },
  });
  const didSync = useRef(false);
  useEffect(() => {
    didSync.current = false;
  }, [demoDataEnabled]);
  useEffect(() => {
    if (!demoDataEnabled) return;
    if (didSync.current || !hasApiConfiguration || sessions.isLoading || sessions.isError) return;
    didSync.current = true;
    syncLibrary.mutate();
  }, [demoDataEnabled, sessions.isError, sessions.isLoading, syncLibrary.mutate]);
  const omiStatus = useQuery({
    queryKey: ["omi-status"],
    queryFn: hakiApi.omiStatus,
    enabled: hasApiConfiguration,
    retry: false,
  });
  const omiLinked = Boolean(omiStatus.data?.linked || health.data?.omi_miniapp?.linked);
  const omiStatusResolved = !hasApiConfiguration || omiStatus.isFetched || omiStatus.isError;
  useEffect(() => {
    if (omiStatusResolved && !omiLinked && source === "omi") setSource("mic");
  }, [omiLinked, omiStatusResolved, source]);

  const visibleSessions = filterDemoSessions(sessions.data ?? [], demoDataEnabled);
  const visibleMatters = filterDemoMatters(matters.data ?? [], demoDataEnabled);
  const demoMatterIds = new Set(
    (matters.data ?? [])
      .filter((matter) => !visibleMatters.some((visible) => visible.id === matter.id))
      .map((matter) => matter.id),
  );
  const visibleContacts = filterDemoContacts(contacts.data ?? [], demoDataEnabled, demoMatterIds);
  const sessionCount = visibleSessions.length;
  const matterCount = visibleMatters.length;
  const readyCount = visibleSessions.filter(
    (session) => session.status === "ready" || session.status === "exported",
  ).length;

  function refreshLibrary() {
    if (demoDataEnabled) {
      syncLibrary.mutate();
      return;
    }
    void sessions.refetch();
    void matters.refetch();
    void contacts.refetch();
  }

  return (
    <PageShell back>
      <main>
        <section className="border-b border-border bg-card/50">
          <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
            <SectionEyebrow>
              Private workspace{practiceName ? ` · ${practiceName}` : ""}
            </SectionEyebrow>
            <div className="mt-3 grid gap-7 lg:grid-cols-[minmax(0,1fr)_24.5rem] lg:items-start lg:gap-14">
              <div className="max-w-2xl">
                <h1 className="font-serif text-4xl font-semibold leading-tight sm:text-5xl">
                  Open a secure session.
                </h1>
                <p className="mt-4 max-w-xl text-base leading-7 text-muted-foreground">
                  Start listening or return to work already in progress. Session titles,
                  transcripts, and results remain within this workspace.
                </p>
                <div className="mt-6 flex flex-wrap gap-2">
                  <Badge variant="outline">
                    <LockKeyhole /> Private record
                  </Badge>
                  <Badge variant="outline">
                    <ShieldCheck /> Source traceable
                  </Badge>
                  <Badge variant="outline">African languages</Badge>
                </div>
              </div>
              <div className="desk-card relative overflow-hidden rounded-lg border border-border p-4 sm:p-6">
                <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary via-action to-primary" />
                <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
                  <div>
                    <h2 className="font-serif text-2xl font-semibold">Start a session</h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Listen first. Choose the work later.
                    </p>
                  </div>
                  <span className="grid size-10 place-items-center rounded-full bg-action/12 text-action">
                    {source === "mic" ? (
                      <Mic className="size-4" />
                    ) : (
                      <Headphones className="size-4" />
                    )}
                  </span>
                </div>
                <label
                  className="mt-6 block text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground"
                  htmlFor="session-title"
                >
                  Session title
                </label>
                <Input
                  id="session-title"
                  className="mt-2 h-11 bg-background"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="e.g. Wanjiku client meeting"
                />
                <div
                  className="mt-5 grid grid-cols-2 gap-1 rounded-md bg-muted p-1"
                  aria-label="Recording source"
                >
                  {(["mic", "omi"] as const).map((item) => {
                    const Icon = item === "mic" ? Mic : Headphones;
                    const omiDisabled = item === "omi" && !omiLinked;
                    return (
                      <Button
                        key={item}
                        type="button"
                        variant={source === item ? "default" : "ghost"}
                        className="h-11 min-w-0 px-2 shadow-none sm:px-4"
                        disabled={omiDisabled}
                        title={
                          omiDisabled ? "Connect Omi under Settings → Connectors first" : undefined
                        }
                        onClick={() => {
                          if (omiDisabled) return;
                          setSource(item);
                        }}
                      >
                        <Icon className="shrink-0" />
                        <span className="truncate">
                          {item === "mic" ? "Microphone" : "Omi wearable"}
                        </span>
                      </Button>
                    );
                  })}
                </div>
                {omiStatusResolved && !omiLinked ? (
                  <p className="mt-3 text-xs leading-5 text-muted-foreground">
                    Connect Omi under{" "}
                    <Link
                      to="/settings"
                      search={{ section: "connectors" }}
                      className="underline underline-offset-2"
                    >
                      Settings → Connectors
                    </Link>{" "}
                    to start sessions from the wearable.
                  </p>
                ) : null}
                <label
                  className="mt-5 block text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground"
                  htmlFor="language"
                >
                  Language
                </label>
                <select
                  id="language"
                  value={language}
                  onChange={(event) => setLanguage(event.target.value)}
                  className="mt-2 h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                >
                  <optgroup label="Code-switch / pairs">
                    {LANGUAGE_OPTIONS.filter((o) => o.group === "pairs").map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Monolingual">
                    {LANGUAGE_OPTIONS.filter((o) => o.group === "mono").map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </optgroup>
                </select>
                {wantsSaharaRefine && !intronLinked ? (
                  <p className="mt-3 text-xs leading-5 text-muted-foreground">
                    Live captions use Whisper. After Stop, HakiScribe refines with Intron Sahara
                    when connected under{" "}
                    <Link
                      to="/settings"
                      search={{ section: "connectors" }}
                      className="underline underline-offset-2"
                    >
                      Settings → Connectors
                    </Link>
                    . African code-switching is also auto-detected from live captions.
                  </p>
                ) : null}
                {wantsSaharaRefine && intronLinked ? (
                  <p className="mt-3 text-xs leading-5 text-muted-foreground">
                    Intron Sahara is connected — live Whisper captions refine to a legal
                    court-hearing transcript when you Stop (keep recordings under ~90 seconds).
                    Mixed African/English speech is also auto-detected mid-session.
                  </p>
                ) : null}
                {!wantsSaharaRefine && intronLinked ? (
                  <p className="mt-3 text-xs leading-5 text-muted-foreground">
                    Intron Sahara is connected. If live captions show African–English mixing,
                    HakiScribe will refine with Sahara automatically on Stop.
                  </p>
                ) : null}
                {source === "omi" && omiLinked ? (
                  <div className="mt-4 space-y-2 rounded-lg border border-border bg-background px-3 py-2 text-xs leading-5 text-muted-foreground">
                    <p>
                      Omi is connected. Speak with the wearable — HakiScribe opens or attaches a
                      session automatically. You can still open a desk session here to watch
                      captions live.
                    </p>
                  </div>
                ) : null}
                <Button
                  variant="warm"
                  size="lg"
                  className="mt-6 h-14 w-full text-base"
                  onClick={() => create.mutate()}
                  disabled={
                    create.isPending || !hasApiConfiguration || (source === "omi" && !omiLinked)
                  }
                >
                  <span className="size-2.5 animate-live-dot rounded-full bg-action-foreground" />
                  {create.isPending
                    ? "Opening session…"
                    : source === "mic"
                      ? "Start recording"
                      : "Start listening via Omi"}
                </Button>
                {demoDataEnabled ? (
                  <>
                    <Button
                      variant="outline"
                      className="mt-2 h-11 w-full"
                      onClick={() => showcase.mutate()}
                      disabled={showcase.isPending || !hasApiConfiguration}
                    >
                      {showcase.isPending
                        ? "Building the Wanjiru showcase…"
                        : "Open a completed judge demo"}
                    </Button>
                    <Button
                      variant="outline"
                      className="mt-2 h-11 w-full"
                      onClick={() => saharaDemo.mutate()}
                      disabled={saharaDemo.isPending || !hasApiConfiguration}
                    >
                      {saharaDemo.isPending
                        ? "Building multilingual sessions…"
                        : "Open multilingual court & client demos"}
                    </Button>
                  </>
                ) : null}
                {create.error && (
                  <p className="mt-3 text-sm text-destructive">
                    {friendlyErrorMessage(
                      create.error,
                      "The session could not be opened. Try again.",
                    )}
                  </p>
                )}
                {demoDataEnabled && showcase.error && (
                  <p className="mt-3 text-sm text-destructive">
                    {friendlyErrorMessage(
                      showcase.error,
                      "The demo session could not be opened. Try again.",
                    )}
                  </p>
                )}
                {demoDataEnabled && saharaDemo.error && (
                  <p className="mt-3 text-sm text-destructive">
                    {friendlyErrorMessage(
                      saharaDemo.error,
                      "Those sessions could not be opened. Try again.",
                    )}
                  </p>
                )}
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-9 sm:px-6 sm:py-12">
          {hasApiConfiguration && !sessions.error && (
            <div className="mb-10 grid gap-3 sm:grid-cols-3">
              {[
                {
                  label: "Sessions in the library",
                  value: sessions.isLoading ? "—" : String(sessionCount),
                },
                {
                  label: "Matters on the desk",
                  value: matters.isLoading ? "—" : String(matterCount),
                },
                { label: "Ready to reopen", value: sessions.isLoading ? "—" : String(readyCount) },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="chamber-card rounded-xl border border-border px-5 py-4"
                >
                  <p className="font-serif text-3xl font-semibold tabular-nums">{stat.value}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.14em] text-muted-foreground">
                    {stat.label}
                  </p>
                </div>
              ))}
            </div>
          )}
          <SectionHeading
            eyebrow="Session library"
            title="Past sessions"
            action={
              <div className="flex flex-wrap items-center justify-end gap-2">
                {visibleSessions.length > 0 && (
                  <span className="hidden text-sm text-muted-foreground sm:inline">
                    {visibleSessions.length} total
                  </span>
                )}
                <TooltipProvider delayDuration={200}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        aria-label={
                          demoDataEnabled ? "Restore demo library" : "Refresh the library"
                        }
                        disabled={
                          (demoDataEnabled ? syncLibrary.isPending : sessions.isFetching) ||
                          !hasApiConfiguration
                        }
                        onClick={() => refreshLibrary()}
                      >
                        <RefreshCw
                          className={
                            (demoDataEnabled ? syncLibrary.isPending : sessions.isFetching)
                              ? "animate-spin"
                              : undefined
                          }
                        />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      {demoDataEnabled ? "Restore demo library" : "Refresh the library"}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <Button asChild variant="outline" size="sm">
                  <Link to="/tracker">Case tracker</Link>
                </Button>
                <Button asChild variant="outline" size="sm">
                  <Link to="/settings">Settings</Link>
                </Button>
              </div>
            }
          />
          {!hasApiConfiguration && (
            <ConnectionError message="Add VITE_API_BASE_URL to connect the HakiScribe frontend to the FastAPI service." />
          )}
          {sessions.error && (
            <ConnectionError
              message={friendlyErrorMessage(sessions.error)}
              retry={() => void sessions.refetch()}
            />
          )}
          {sessions.isLoading && (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-24 animate-pulse rounded-xl border border-border bg-card"
                />
              ))}
            </div>
          )}
          {demoDataEnabled && sessions.data?.length === 0 && syncLibrary.isPending && (
            <div className="chamber-card rounded-xl border border-dashed border-border py-14 text-center">
              <p className="font-serif text-xl">Restoring the desk</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Bringing the seed library back onto this instance.
              </p>
            </div>
          )}
          {!sessions.isLoading &&
            visibleSessions.length === 0 &&
            !(demoDataEnabled && syncLibrary.isPending) && (
              <div className="chamber-card rounded-xl border border-dashed border-border py-14 text-center">
                <p className="font-serif text-xl">
                  {demoDataEnabled ? "The library is empty" : "No sessions yet"}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  {demoDataEnabled
                    ? "Open the completed Wanjiru client meeting, or start listening."
                    : "Start a private session to begin capturing work. Demo samples stay hidden while Use Demo Data is off."}
                </p>
                {demoDataEnabled ? (
                  <Button
                    className="mt-5"
                    variant="outline"
                    onClick={() => showcase.mutate()}
                    disabled={showcase.isPending || !hasApiConfiguration}
                  >
                    {showcase.isPending ? "Building showcase…" : "Load judge demo"}
                  </Button>
                ) : null}
              </div>
            )}
          <div className="grid gap-3">
            {visibleSessions.map((session) => (
              <SessionRow key={session.id} session={session} />
            ))}
          </div>
          <LegalIntelligence matters={visibleMatters} />
          <LibraryMatters matters={visibleMatters} contacts={visibleContacts} />
        </section>
      </main>
      {health.data?.integrations && (
        <div className="mx-auto max-w-6xl px-4 pb-4 sm:px-6">
          <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
            Live integrations:{" "}
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
      className="chamber-card group grid grid-cols-[auto_minmax(0,1fr)] items-center gap-3 rounded-lg border border-border p-4 transition-all hover:border-primary/30 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:gap-4 sm:px-5 sm:hover:-translate-y-0.5"
    >
      <span className="grid size-12 place-items-center rounded-xl bg-secondary text-secondary-foreground">
        <SourceIcon source={session.source} className="size-4" />
      </span>
      <span className="min-w-0">
        <span className="block truncate font-medium text-foreground group-hover:text-primary">
          {session.title}
        </span>
        <span className="mt-1 block text-xs text-muted-foreground">
          {new Date(session.created_at).toLocaleDateString(undefined, {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
          {" · "}
          {session.source === "omi" ? "Omi wearable" : "Microphone"}
          {languageLabel(session.language_hint) || languageLabel(session.detected_language)
            ? ` · ${languageLabel(session.language_hint) || languageLabel(session.detected_language)}`
            : ""}
        </span>
        {(matterNames.length > 0 ||
          contactNames.length > 0 ||
          (session.generated_types?.length ?? 0) > 0) && (
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
            {matterNames.map((name) => (
              <Badge key={name} variant="secondary">
                {name}
              </Badge>
            ))}
            {contactNames.map((name) => (
              <Badge key={name} variant="outline">
                {name}
              </Badge>
            ))}
          </span>
        )}
      </span>
      <span className="col-start-2 justify-self-start sm:col-start-3 sm:row-start-1 sm:justify-self-end">
        <StatusBadge status={session.status} />
      </span>
    </Link>
  );
}

function LibraryMatters({ matters, contacts }: { matters: Matter[]; contacts: Contact[] }) {
  const contactsByMatter = (matterId: string) =>
    contacts.filter((contact) => contact.matter_id === matterId);
  return (
    <div className="mt-16">
      <SectionHeading
        eyebrow="Workspace"
        title="Matters and contacts"
        action={
          <span className="text-sm text-muted-foreground">
            {matters.length} matter{matters.length === 1 ? "" : "s"}
          </span>
        }
      />
      {matters.length === 0 && (
        <div className="chamber-card rounded-xl border border-dashed border-border py-12 text-center text-muted-foreground">
          Generated workspace matters and linked contacts will persist here.
        </div>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        {matters.map((matter) => {
          const linked = contactsByMatter(matter.id);
          const initials = matter.client_name
            .split(" ")
            .filter(Boolean)
            .slice(0, 2)
            .map((part) => part[0])
            .join("")
            .toUpperCase();
          return (
            <article key={matter.id} className="chamber-card rounded-xl border border-border p-5">
              <div className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-3">
                <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-primary text-sm font-semibold text-primary-foreground">
                  {initials || <BriefcaseBusiness className="size-4" />}
                </span>
                <div className="min-w-0">
                  <h3 className="font-semibold text-foreground">{matter.matter_name}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">Client: {matter.client_name}</p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {linked.length === 0 && (
                      <span className="text-xs text-muted-foreground">No linked contacts yet</span>
                    )}
                    {linked.map((contact) => (
                      <Badge key={contact.id} variant="outline">
                        {contact.name}
                      </Badge>
                    ))}
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
  const detail = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => hakiApi.getSession(sessionId),
    retry: false,
  });
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

  if (detail.isLoading || !step)
    return (
      <PageShell back>
        <main className="mx-auto max-w-4xl px-4 py-24">
          <div className="mx-auto h-1 w-48 origin-left animate-reading-line bg-primary" />
          <p className="mt-6 text-center font-serif text-xl">Opening secure session…</p>
        </main>
      </PageShell>
    );
  if (detail.error || !detail.data)
    return (
      <PageShell back>
        <main className="mx-auto max-w-3xl px-4 py-16">
          <ConnectionError
            message={detail.error?.message ?? "Session not found"}
            retry={() => void detail.refetch()}
          />
        </main>
      </PageShell>
    );

  const session = detail.data;
  if (step === "recording")
    return (
      <RecordingScreen
        session={session}
        onStopped={(next) => {
          queryClient.setQueryData(["session", sessionId], next);
          setStep("speakers");
        }}
      />
    );
  if (step === "speakers")
    return (
      <SpeakerScreen
        session={session}
        onNext={async () => {
          await detail.refetch();
          setStep("redact");
        }}
      />
    );
  if (step === "redact")
    return <RedactScreen session={session} onNext={() => setStep("analyzing")} />;
  if (step === "analyzing")
    return (
      <AnalyzingScreen
        sessionId={session.id}
        onComplete={async (actions) => {
          queryClient.setQueryData(["session", sessionId], (current: SessionDetail | undefined) =>
            current ? { ...current, detected_actions: actions } : current,
          );
          await detail.refetch();
          setStep("tray");
        }}
      />
    );
  return (
    <PageShell back>
      <ActionWorkspace
        session={session}
        initialResults={session.action_results ?? []}
        showResults={step === "results"}
        onResults={() => setStep("results")}
        onTray={() => setStep("tray")}
        onVerify={() => setStep("speakers")}
      />
    </PageShell>
  );
}

function RecordingScreen({
  session,
  onStopped,
}: {
  session: SessionDetail;
  onStopped: (detail: SessionDetail) => void;
}) {
  const startedAt = useRef(Date.now());
  const omiStatus = useQuery({
    queryKey: ["omi-status"],
    queryFn: hakiApi.omiStatus,
    enabled: hasApiConfiguration && session.source === "omi",
    retry: false,
  });
  const omiLinked = Boolean(omiStatus.data?.linked);
  useEffect(() => {
    // Route live Omi transcripts from the app-store link into this session.
    if (hasApiConfiguration && session.source === "omi" && omiLinked) {
      void hakiApi.omiSetActive(session.id).catch(() => undefined);
    }
  }, [omiLinked, session.id, session.source]);
  const recorder = useRef<MediaRecorder | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const audioChunks = useRef<Blob[]>([]);
  const stopping = useRef(false);
  const [elapsed, setElapsed] = useState(0);
  const [captions, setCaptions] = useState(session.transcript ?? []);
  const [flags, setFlags] = useState(session.flagged_moments ?? []);
  const [error, setError] = useState<string | null>(null);
  const [stoppingNow, setStoppingNow] = useState(false);
  const [refiningSahara, setRefiningSahara] = useState(false);

  const languageMix = useMemo(() => {
    const text = captions.map((line) => line.text).join(" ");
    return detectLanguageMix(text);
  }, [captions]);
  const mixBadge = detectedModeLabel(languageMix.mode);
  const willAutoRefine = shouldAutoSaharaRefine(session.language_hint, languageMix.mode);

  useEffect(() => {
    const timer = window.setInterval(() => setElapsed(Date.now() - startedAt.current), 1000);
    if (session.source === "mic") {
      void navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((mediaStream) => {
          stream.current = mediaStream;
          audioChunks.current = [];
          const ws = new WebSocket(websocketUrl(session.id));
          socket.current = ws;
          ws.onmessage = (event) => {
            try {
              setCaptions((current) => [
                ...current,
                JSON.parse(event.data as string) as TranscriptSegment,
              ]);
            } catch {
              setError("A transcript update could not be read.");
            }
          };
          ws.onerror = () => {
            if (!stopping.current)
              setError("Live transcription disconnected. Your session remains open.");
          };
          ws.onopen = () => {
            const nextRecorder = new MediaRecorder(mediaStream);
            recorder.current = nextRecorder;
            nextRecorder.ondataavailable = (event) => {
              if (event.data.size) {
                audioChunks.current.push(event.data);
                if (ws.readyState === WebSocket.OPEN) ws.send(event.data);
              }
            };
            // Backend timestamps each chunk as 3s — keep the client in step.
            nextRecorder.start(3000);
          };
        })
        .catch(() =>
          setError(
            "Microphone access is required for a Mic session. Allow access, then reopen this session.",
          ),
        );
    } else {
      const poll = window.setInterval(() => {
        void hakiApi
          .getSession(session.id)
          .then((next) => {
            setCaptions(next.transcript ?? []);
            setFlags(next.flagged_moments ?? []);
          })
          .catch(() => undefined);
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
      const moment = await hakiApi.flagMoment(session.id, {
        at_ms: elapsed,
        ...(label ? { label } : {}),
      });
      setFlags((current) => [...current, moment]);
      toast.success(label ? `Flagged: ${label}` : "Moment flagged");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The moment could not be flagged.");
    }
  };
  const stop = async () => {
    setStoppingNow(true);
    stopping.current = true;
    if (recorder.current?.state === "recording") {
      await new Promise<void>((resolve) => {
        const active = recorder.current;
        if (!active) {
          resolve();
          return;
        }
        active.onstop = () => resolve();
        active.stop();
      });
    }
    socket.current?.close();
    stream.current?.getTracks().forEach((track) => track.stop());
    try {
      let detail: SessionDetail;
      if (session.source === "omi") {
        // Unlike the microphone WebSocket, Omi has no connection-close event
        // that can finalize the desk session for us.
        await hakiApi.finalize(session.id);
      }
      const detectedMode = detectLanguageMix(captions.map((line) => line.text).join(" ")).mode;
      const shouldRefine =
        session.source === "mic" &&
        shouldAutoSaharaRefine(session.language_hint, detectedMode) &&
        audioChunks.current.length > 0;
      if (shouldRefine) {
        const health = await hakiApi.health().catch(() => null);
        const intronOn = Boolean(health?.integrations?.["intron"]);
        if (intronOn) {
          setRefiningSahara(true);
          const blob = new Blob(audioChunks.current, {
            type: audioChunks.current[0]?.type || "audio/webm",
          });
          try {
            detail = await hakiApi.finalizeAsr(session.id, blob, "recording.webm", detectedMode);
            toast.success(
              detectedMode === "code-switch" || detectedMode === "multilingual"
                ? "Code-switching detected — transcript refined with Intron Sahara"
                : "Transcript refined with Intron Sahara",
            );
          } catch (caught) {
            toast.error(
              friendlyErrorMessage(
                caught instanceof Error ? caught : new Error("Sahara refine failed"),
                "Kept live captions — Sahara refine failed.",
              ),
            );
            detail = await hakiApi.getSession(session.id);
          } finally {
            setRefiningSahara(false);
          }
        } else {
          toast.info(
            "Connect Intron Sahara in Settings to refine African / code-switched transcripts.",
          );
          detail = await hakiApi.getSession(session.id);
        }
      } else {
        detail = await hakiApi.getSession(session.id);
      }
      onStopped(detail);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The session could not be loaded.");
      setStoppingNow(false);
      setRefiningSahara(false);
    }
  };

  return (
    <div className="relative flex min-h-[100svh] flex-col overflow-hidden bg-primary text-primary-foreground">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_18%,oklch(1_0_0/0.08),transparent_42%)]" />
      <header className="relative z-10 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-primary-foreground/15 px-4 py-3 sm:px-8 sm:py-4">
        <span className="font-serif text-xl font-semibold">HakiScribe</span>
        <div className="flex flex-wrap items-center justify-end gap-2">
          {mixBadge && willAutoRefine ? (
            <span className="inline-flex max-w-[14rem] items-center gap-1.5 rounded-full border border-action/40 bg-action/15 px-3 py-1 text-[10px] leading-snug text-primary-foreground sm:max-w-none sm:text-xs">
              <Globe className="size-3 shrink-0" />
              <span className="truncate sm:whitespace-normal">{mixBadge}</span>
            </span>
          ) : null}
          <span className="inline-flex items-center gap-2 rounded-full border border-primary-foreground/20 bg-primary-foreground/10 px-3 py-1 text-xs">
            <span className="size-2 animate-live-dot rounded-full bg-action" /> Recording
          </span>
        </div>
      </header>
      <main className="relative z-10 mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-5 sm:px-8 sm:py-8">
        <div className="text-center">
          <p className="text-sm text-primary-foreground/70">{session.title}</p>
          <div className="relative mx-auto mt-3 grid size-36 place-items-center sm:mt-5 sm:size-52">
            <span className="absolute inset-0 rounded-full border border-primary-foreground/15 animate-pulse-ring" />
            <span className="absolute inset-4 rounded-full border border-primary-foreground/10" />
            <p className="relative font-mono text-4xl tabular-nums sm:text-6xl">
              {formatDuration(elapsed)}
            </p>
          </div>
        </div>
        <div className="mt-6 flex min-h-8 gap-2 overflow-x-auto pb-2">
          {flags.map((item) => (
            <span
              key={item.id}
              className="shrink-0 rounded-full border border-primary-foreground/20 bg-primary-foreground/10 px-3 py-1.5 text-xs"
            >
              {formatDuration(item.at_ms)} · {item.label ?? "Flagged moment"}
            </span>
          ))}
        </div>
        <div
          className="my-4 flex h-16 items-center justify-center gap-1 sm:my-7 sm:h-24"
          aria-label="Live audio waveform"
        >
          {Array.from({ length: 32 }, (_, index) => (
            <span
              key={index}
              className={cn(
                "h-12 w-1 rounded-full bg-primary-foreground/75 animate-waveform sm:h-16",
                index % 3 === 1 && "[animation-delay:180ms]",
                index % 3 === 2 && "[animation-delay:360ms]",
              )}
            />
          ))}
        </div>
        <div className="mb-3 flex flex-wrap justify-center gap-2">
          {flagLabels.map((label) => (
            <Button
              key={label}
              variant="quiet"
              size="sm"
              className="border-primary-foreground/20 bg-primary-foreground/10 text-primary-foreground hover:bg-primary-foreground/20"
              onClick={() => void flag(label)}
            >
              {label}
            </Button>
          ))}
        </div>
        <Button
          variant="warm"
          className="mx-auto h-20 w-full max-w-md text-lg shadow-lg sm:h-24 sm:text-xl"
          onClick={() => void flag()}
        >
          <Flag className="size-7" /> Flag this moment
        </Button>
        <div className="mt-5 min-h-20 rounded-lg border border-primary-foreground/10 bg-primary-foreground/5 px-4 py-3 sm:mt-8 sm:min-h-24 sm:py-4">
          {session.source === "omi" && !captions.length ? (
            <div className="space-y-3 text-sm text-primary-foreground/80">
              <p className="flex items-center justify-center gap-2">
                <Radio className="size-4" />{" "}
                {omiLinked
                  ? "Listening for Omi. Incoming segments appear here."
                  : "Listening via Omi. Incoming segments appear here."}
              </p>
              {omiLinked ? (
                <p className="text-center text-xs text-primary-foreground/65">
                  Miniapp is linked. Speak into the wearable — no paste required.
                </p>
              ) : null}
              <details className="rounded-md bg-primary-foreground/8 px-3 py-2 text-left">
                <summary className="cursor-pointer text-xs text-primary-foreground/70">
                  Advanced pairing URL
                </summary>
                <p className="mt-2 break-all font-mono text-[11px] text-primary-foreground/70">
                  {omiWebhookUrl(session.id, omiStatus.data?.webhook_url)}
                </p>
                <div className="mt-2 flex justify-center">
                  <Button
                    variant="quiet"
                    size="sm"
                    className="border-primary-foreground/20 bg-primary-foreground/10 text-primary-foreground hover:bg-primary-foreground/20"
                    onClick={() => {
                      void navigator.clipboard.writeText(
                        omiWebhookUrl(session.id, omiStatus.data?.webhook_url),
                      );
                      toast.success("Omi webhook copied");
                    }}
                  >
                    <Copy /> Copy pairing URL
                  </Button>
                </div>
              </details>
            </div>
          ) : (
            <div className="max-h-28 space-y-2 overflow-y-auto text-sm italic text-primary-foreground/65">
              {captions.slice(-4).map((line) => (
                <p key={line.id}>
                  <span className="font-semibold not-italic">{line.speaker ?? "Speaker"}:</span>{" "}
                  {line.text}
                </p>
              ))}
              {!captions.length && (
                <p className="text-center">Live captions will appear here as people speak.</p>
              )}
            </div>
          )}
        </div>
        {error && <p className="mt-4 text-center text-sm text-primary-foreground">{error}</p>}
        <div className="safe-bottom mt-auto flex flex-col items-center pt-5 sm:pt-8">
          <Button
            variant="quiet"
            className="h-12 w-full max-w-md border-primary-foreground/25 bg-primary-foreground/10 text-primary-foreground hover:bg-primary-foreground/20 sm:w-auto sm:min-w-36"
            onClick={() => void stop()}
            disabled={stoppingNow}
          >
            <Square className="fill-current" />{" "}
            {refiningSahara ? "Refining with Sahara…" : stoppingNow ? "Stopping…" : "Stop"}
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
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        Flagged in the room
      </p>
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
  const speakers = useMemo(
    () =>
      Array.from(
        new Set(session.transcript.map((s) => s.speaker).filter((s): s is string => Boolean(s))),
      ),
    [session.transcript],
  );
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const mutation = useMutation({
    mutationFn: () => hakiApi.updateSpeakers(session.id, mapping),
    onSuccess: onNext,
  });
  return (
    <PageShell back>
      <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <FlowProgress current={1} labels={["Speakers", "Privilege", "Actions"]} />
        <FlowHeader
          step="Verify the record"
          title="Who was speaking?"
          copy="Names entered here flow into legal documents. Review them deliberately, or keep the original labels."
        />
        <div className="chamber-card divide-y divide-border overflow-hidden rounded-xl border border-border">
          {speakers.map((speaker) => (
            <div
              key={speaker}
              className="grid gap-2 px-4 py-5 sm:grid-cols-[10rem_1fr] sm:items-center"
            >
              <label className="text-sm font-semibold" htmlFor={`speaker-${speaker}`}>
                {speaker}
              </label>
              <Input
                id={`speaker-${speaker}`}
                className="h-11 bg-background"
                placeholder="Type their real name"
                value={mapping[speaker] ?? ""}
                onChange={(event) =>
                  setMapping((current) => ({ ...current, [speaker]: event.target.value }))
                }
              />
            </div>
          ))}
        </div>
        {!speakers.length && (
          <p className="chamber-card rounded-xl border border-dashed border-border py-8 text-center text-muted-foreground">
            No speaker labels were found. You can continue to the transcript check.
          </p>
        )}
        {mutation.error && (
          <p className="mt-4 text-sm text-destructive">{friendlyErrorMessage(mutation.error)}</p>
        )}
        <div className="mt-8 grid grid-cols-2 gap-3 sm:flex sm:justify-end">
          <Button variant="ghost" className="h-11" onClick={onNext}>
            Skip
          </Button>
          <Button
            className="h-11"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !Object.values(mapping).some((name) => name.trim())}
          >
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
    setSegments((current) =>
      current.map((item) => (item.id === segment.id ? { ...item, redacted: nextValue } : item)),
    );
    try {
      await hakiApi.redactSegment(session.id, segment.id, nextValue);
    } catch (caught) {
      setSegments((current) => current.map((item) => (item.id === segment.id ? segment : item)));
      setError(
        caught instanceof Error ? caught.message : "The privacy setting could not be changed.",
      );
    }
  };
  const continueFlow = async () => {
    await queryClient.invalidateQueries({ queryKey: ["session", session.id] });
    onNext();
  };
  return (
    <PageShell back>
      <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
        <FlowProgress current={2} labels={["Speakers", "Privilege", "Actions"]} />
        <FlowHeader
          step="Verify the record"
          title="Protect what stays private"
          copy="Lock any privileged or off-record line. It stays visible to you, but will not be sent for analysis."
        />
        <FlaggedMomentsBar flags={session.flagged_moments} />
        {error && <ConnectionError message={error} />}
        <div className="chamber-card mt-2 divide-y divide-border overflow-hidden rounded-xl border border-border">
          {segments.map((segment) => (
            <div
              key={segment.id}
              className={cn(
                "grid grid-cols-[1fr_auto] gap-4 px-4 py-4 sm:px-5",
                segment.redacted && "bg-privileged/70 text-muted-foreground",
              )}
            >
              <div>
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold text-primary">
                    {segment.speaker ?? "Speaker"}
                  </span>
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {formatDuration(segment.start_ms)}
                  </span>
                  {segment.redacted && (
                    <Badge
                      variant="outline"
                      className="border-privileged-foreground/30 text-privileged-foreground"
                    >
                      Won't be used
                    </Badge>
                  )}
                </div>
                <p
                  className={cn(
                    "font-serif text-base leading-7",
                    segment.redacted && "line-through decoration-privileged-foreground/50",
                  )}
                >
                  {segment.text}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                aria-label={segment.redacted ? "Include this line" : "Mark privileged"}
                title={segment.redacted ? "Include this line" : "Mark privileged"}
                onClick={() => void toggle(segment)}
              >
                {segment.redacted ? (
                  <LockKeyhole className="text-privileged-foreground" />
                ) : (
                  <UnlockKeyhole />
                )}
              </Button>
            </div>
          ))}
        </div>
        {!segments.length && (
          <p className="chamber-card rounded-xl border border-dashed border-border py-10 text-center text-muted-foreground">
            No transcript segments have arrived yet. You can still continue and analyze the
            available session data.
          </p>
        )}
        <div className="safe-bottom sticky bottom-0 z-20 mt-6 border-t border-border bg-background/95 py-3 text-right backdrop-blur-md sm:py-4">
          <Button size="lg" className="w-full sm:w-auto" onClick={() => void continueFlow()}>
            Continue to analysis
          </Button>
        </div>
      </main>
    </PageShell>
  );
}

function AnalyzingScreen({
  sessionId,
  onComplete,
}: {
  sessionId: string;
  onComplete: (actions: DetectedAction[]) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;
  useEffect(() => {
    let active = true;
    void hakiApi
      .finalize(sessionId)
      .then(() => hakiApi.detect(sessionId))
      .then((actions) => {
        if (active) void onCompleteRef.current(actions);
      })
      .catch((caught) => {
        if (active)
          setError(caught instanceof Error ? caught.message : "Analysis could not be completed.");
      });
    return () => {
      active = false;
    };
  }, [sessionId]);
  return (
    <PageShell back>
      <main className="mx-auto flex min-h-[70vh] max-w-xl flex-col items-center justify-center px-5 text-center">
        <FlowProgress current={3} labels={["Speakers", "Privilege", "Actions"]} />
        <div className="w-48 space-y-2" aria-hidden>
          {[0, 1, 2, 3].map((item) => (
            <div
              key={item}
              className="h-1 origin-left animate-reading-line bg-primary"
              style={{ animationDelay: `${item * 220}ms` }}
            />
          ))}
        </div>
        <h1 className="mt-10 font-serif text-3xl font-semibold">Reviewing what happened…</h1>
        <p className="mt-3 leading-7 text-muted-foreground">
          Checking the verified record for documents, dates, matters, contacts, notes, and billable
          work. Flagged moments are weighed first. Redacted lines stay out.
        </p>
        <TrustLine className="mt-5" />
        {error && (
          <div className="mt-8 w-full">
            <ConnectionError message={error} retry={() => window.location.reload()} />
          </div>
        )}
      </main>
    </PageShell>
  );
}

function ActionWorkspace({
  session,
  initialResults,
  showResults,
  onResults,
  onTray,
  onVerify,
}: {
  session: SessionDetail;
  initialResults: ActionResult[];
  showResults: boolean;
  onResults: () => void;
  onTray: () => void;
  onVerify: () => void;
}) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"tray" | "record" | "results">(showResults ? "results" : "tray");
  const [selected, setSelected] = useState(
    () =>
      new Set(
        session.detected_actions
          .filter((action) => action.pre_checked && action.status !== "dismissed")
          .map((action) => action.id),
      ),
  );
  const [actions, setActions] = useState(session.detected_actions);
  const [results, setResults] = useState(initialResults);
  const [showDismissed, setShowDismissed] = useState(false);
  useEffect(() => {
    setActions(session.detected_actions);
    setSelected(
      new Set(
        session.detected_actions
          .filter((action) => action.pre_checked && action.status !== "dismissed")
          .map((action) => action.id),
      ),
    );
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
        actions
          .filter((action) => ids.includes(action.id))
          .map((action) => [action.id, action.extracted_fields]),
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
  const select = (id: string, checked: boolean) =>
    setSelected((current) => {
      const next = new Set(current);
      checked ? next.add(id) : next.delete(id);
      return next;
    });
  const dismiss = async (id: string) => {
    try {
      const next = await hakiApi.dismissAction(session.id, id);
      setActions((current) => current.map((item) => (item.id === id ? next : item)));
      select(id, false);
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : "The action could not be dismissed.");
    }
  };
  return (
    <main className="mx-auto max-w-6xl px-4 py-7 sm:px-6 sm:py-10">
      <div className="flex flex-col justify-between gap-5 border-b border-border pb-8 sm:flex-row sm:items-end">
        <div className="min-w-0">
          <SectionEyebrow>
            {tab === "results"
              ? "Generated work"
              : tab === "record"
                ? "Verified record"
                : "Action tray"}
          </SectionEyebrow>
          <h1 className="mt-2 break-words font-serif text-3xl font-semibold leading-tight sm:text-4xl">
            {session.title}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {tab === "results"
              ? "Review and edit before anything leaves your workspace."
              : tab === "record"
                ? "The same record the tray used, including what you locked."
                : `${visibleActions.length} possible legal actions, each grounded in the transcript.`}
          </p>
        </div>
        <div className="grid gap-2 sm:flex sm:flex-wrap sm:items-center">
          <Button variant="outline" size="sm" className="w-full sm:w-auto" onClick={onVerify}>
            Back to verify
          </Button>
          <TrustLine className="max-w-full rounded-md border border-border bg-card px-3 py-2 text-left sm:rounded-full sm:py-1.5" />
        </div>
      </div>
      <FlaggedMomentsBar flags={session.flagged_moments} />
      <div
        className={cn(
          "mt-6 grid gap-1 rounded-lg bg-muted p-1",
          results.length > 0 ? "grid-cols-3" : "grid-cols-2",
        )}
      >
        <Button
          variant={tab === "tray" ? "default" : "ghost"}
          className="h-11 min-w-0 px-2 shadow-none"
          onClick={() => {
            setTab("tray");
            onTray();
          }}
        >
          <span className="truncate">Actions</span>
        </Button>
        <Button
          variant={tab === "record" ? "default" : "ghost"}
          className="h-11 min-w-0 px-2 shadow-none"
          onClick={() => setTab("record")}
        >
          <span className="truncate">Transcript</span>
        </Button>
        {results.length > 0 && (
          <Button
            variant={tab === "results" ? "default" : "ghost"}
            className="h-11 min-w-0 px-2 shadow-none"
            onClick={() => {
              setTab("results");
              onResults();
            }}
          >
            <span className="truncate">Results ({results.length})</span>
          </Button>
        )}
      </div>
      {tab === "record" ? (
        <TranscriptPanel transcript={session.transcript} actions={visibleActions} />
      ) : tab === "results" && results.length ? (
        <>
          <ResultsList results={results} sessionId={session.id} />
          {failedIds.length > 0 && (
            <div className="safe-bottom sticky bottom-0 z-20 mt-6 border-t border-border bg-background/95 py-3 backdrop-blur-md sm:static sm:border-0 sm:bg-transparent sm:py-0 sm:backdrop-blur-none">
              <Button
                variant="outline"
                className="h-11 w-full sm:mt-6 sm:w-auto"
                disabled={generate.isPending}
                onClick={() => generate.mutate(failedIds)}
              >
                <RefreshCw className={cn(generate.isPending && "animate-spin")} />
                Retry failed ({failedIds.length})
              </Button>
            </div>
          )}
        </>
      ) : (
        <>
          <div className="pb-[calc(5.75rem+env(safe-area-inset-bottom,0px))] sm:pb-0">
            <div className="my-6 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
              <p className="text-sm text-muted-foreground">
                Review, edit, then choose what HakiScribe should produce.
              </p>
              <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
                <Button
                  variant="outline"
                  size="sm"
                  className="min-w-0 px-2"
                  onClick={() => setShowDismissed((current) => !current)}
                >
                  {showDismissed ? "Hide dismissed" : "Show dismissed"}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="min-w-0 px-2"
                  onClick={() =>
                    setSelected(
                      new Set(
                        visibleActions
                          .filter((action) => action.pre_checked)
                          .map((action) => action.id),
                      ),
                    )
                  }
                >
                  <Check className="shrink-0" /> <span className="truncate">Select likely</span>
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
                  onFields={(fields) =>
                    setActions((current) =>
                      current.map((item) =>
                        item.id === action.id ? { ...item, extracted_fields: fields } : item,
                      ),
                    )
                  }
                />
              ))}
            </div>
            {!visibleActions.length && (
              <div className="chamber-card rounded-xl border border-dashed border-border py-12 text-center">
                <h2 className="font-serif text-2xl">No actions detected</h2>
                <p className="mt-2 text-muted-foreground">
                  The verified transcript did not contain enough information to propose legal work.
                </p>
              </div>
            )}
            {generate.error && (
              <div className="mt-5">
                <ConnectionError message={friendlyErrorMessage(generate.error)} />
              </div>
            )}

            {/* Desktop / large screens: in-flow CTA under the list */}
            <div className="mt-6 hidden border-t border-border pt-4 sm:block">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-muted-foreground">
                  {selected.size
                    ? `${selected.size} action${selected.size === 1 ? "" : "s"} ready to generate`
                    : "Select at least one action to generate"}
                </p>
                <Button
                  variant="warm"
                  size="lg"
                  className="h-12 min-w-56"
                  disabled={!selected.size || generate.isPending}
                  onClick={() => generate.mutate(Array.from(selected))}
                >
                  {generate.isPending
                    ? "Generating selected work…"
                    : `Generate selected (${selected.size})`}
                </Button>
              </div>
            </div>

            <section
              className="mt-10 space-y-3 border-t border-border pt-8"
              aria-label="More tools"
            >
              <div className="mb-1">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  More tools
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Optional after you generate the selected tray work.
                </p>
              </div>
              <article className="chamber-card rounded-xl border border-border bg-card">
                <div className="grid grid-cols-[auto_1fr] gap-3 p-4 sm:p-5">
                  <span className="grid size-11 place-items-center rounded-xl bg-secondary text-secondary-foreground">
                    <Scale className="size-5" />
                  </span>
                  <div className="min-w-0">
                    <h2 className="font-semibold text-foreground">
                      Kenyan legal research on this matter
                    </h2>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">
                      Case law, statutes and precedent for the issues raised on this record, each
                      with a citation you can open.
                    </p>
                    <Button asChild variant="outline" size="sm" className="mt-3">
                      <Link to="/research" search={{ session: session.id }}>
                        Open research
                      </Link>
                    </Button>
                  </div>
                </div>
              </article>
              <AskComposer
                sessionId={session.id}
                onResult={(result) => {
                  setResults((current) => [
                    result,
                    ...current.filter((item) => item.action_id !== result.action_id),
                  ]);
                  void queryClient.invalidateQueries({ queryKey: ["session", session.id] });
                  onResults();
                }}
              />
              <LegalIntelligence sessionId={session.id} matterId={session.matters?.[0]?.id} />
            </section>
          </div>

          {/* Mobile: fixed dock always within thumb reach while reviewing the tray */}
          <div className="safe-bottom fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 px-4 pt-3 shadow-[0_-8px_24px_oklch(0.25_0.02_150/0.08)] backdrop-blur-md sm:hidden">
            <div className="mx-auto flex max-w-6xl flex-col gap-2">
              <p className="text-center text-xs text-muted-foreground">
                {selected.size
                  ? `${selected.size} selected · ready to generate`
                  : "Select actions above to generate"}
              </p>
              <Button
                variant="warm"
                size="lg"
                className="h-12 w-full"
                disabled={!selected.size || generate.isPending}
                onClick={() => generate.mutate(Array.from(selected))}
              >
                {generate.isPending
                  ? "Generating selected work…"
                  : `Generate selected (${selected.size})`}
              </Button>
            </div>
          </div>
        </>
      )}
    </main>
  );
}

function TranscriptPanel({
  transcript,
  actions,
}: {
  transcript: TranscriptSegment[];
  actions: DetectedAction[];
}) {
  const cited = new Set(actions.map((action) => action.source_segment_id).filter(Boolean));
  return (
    <div className="chamber-card mt-8 divide-y divide-border overflow-hidden rounded-xl border border-border">
      {transcript.map((segment) => (
        <div
          key={segment.id}
          className={cn(
            "px-4 py-4 sm:px-5",
            segment.redacted && "bg-privileged/70 text-muted-foreground",
            cited.has(segment.id) && !segment.redacted && "bg-secondary/40",
          )}
        >
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-primary">
              {segment.speaker ?? "Speaker"}
            </span>
            <span className="font-mono text-[11px] text-muted-foreground">
              {formatDuration(segment.start_ms)}
            </span>
            {segment.redacted && (
              <Badge
                variant="outline"
                className="border-privileged-foreground/30 text-privileged-foreground"
              >
                Won't be used
              </Badge>
            )}
            {cited.has(segment.id) && !segment.redacted && (
              <Badge variant="secondary">Cited in tray</Badge>
            )}
          </div>
          <p
            className={cn(
              "font-serif text-base leading-7",
              segment.redacted && "line-through decoration-privileged-foreground/50",
            )}
          >
            {segment.text}
          </p>
        </div>
      ))}
      {!transcript.length && (
        <p className="px-4 py-10 text-center text-muted-foreground">
          No transcript segments are available.
        </p>
      )}
    </div>
  );
}

function nearestFlag(flags: FlaggedMoment[], source: TranscriptSegment | undefined) {
  if (!source) return undefined;
  return flags.find((flag) => Math.abs(flag.at_ms - source.start_ms) <= 8000);
}

function ActionCard({
  action,
  transcript,
  flags,
  checked,
  onChecked,
  onDismiss,
  onFields,
}: {
  action: DetectedAction;
  transcript: TranscriptSegment[];
  flags: FlaggedMoment[];
  checked: boolean;
  onChecked: (checked: boolean) => void;
  onDismiss: () => void;
  onFields: (fields: Record<string, unknown>) => void;
}) {
  const [open, setOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(false);
  const Icon = actionIcons[action.type];
  const source = transcript.find((segment) => segment.id === action.source_segment_id);
  const flagged = nearestFlag(flags, source);
  const speculative = !action.pre_checked || action.confidence < 0.7;
  const background = action.extracted_fields["background_info"];
  const detectionMode = action.extracted_fields["detection_mode"];
  return (
    <article
      className={cn(
        "chamber-card overflow-hidden rounded-xl border transition-all",
        checked ? "border-primary bg-secondary/20" : "border-border bg-card",
        speculative && !checked && "opacity-70",
        action.status === "dismissed" && "opacity-50",
      )}
    >
      <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] gap-3 p-4 sm:p-5">
        <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-secondary text-secondary-foreground">
          <Icon className="size-5" />
        </span>
        <button type="button" className="min-w-0 text-left" onClick={() => setOpen(!open)}>
          <h2 className="break-words font-semibold text-foreground">{action.title}</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{action.preview}</p>
        </button>
        <Checkbox
          checked={checked}
          onCheckedChange={(value) => onChecked(value === true)}
          aria-label={`Select ${action.title}`}
          className="mt-2 size-5"
          disabled={action.status === "dismissed"}
        />
      </div>
      <div className="grid gap-3 border-t border-border/80 px-4 py-3 text-xs sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:px-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={speculative ? "outline" : "secondary"}>
            {action.confidence_reason ??
              (speculative ? "Suggested from context" : "Clear from the record")}
          </Badge>
          {flagged && (
            <Badge variant="secondary">
              Honours flag{flagged.label ? `: ${flagged.label}` : ""}
            </Badge>
          )}
          {detectionMode === "heuristic" && <Badge variant="outline">From the record</Badge>}
          {background !== undefined && <Badge variant="outline">External research</Badge>}
        </div>
        <div className="flex min-h-8 items-center justify-end gap-4">
          {source && (
            <button
              type="button"
              className="font-semibold text-primary hover:underline"
              onClick={() => setSourceOpen(!sourceOpen)}
            >
              View source
            </button>
          )}
          {action.status !== "dismissed" && (
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground"
              onClick={onDismiss}
            >
              Dismiss
            </button>
          )}
          <button
            type="button"
            aria-label={open ? "Collapse action" : "Edit action"}
            onClick={() => setOpen(!open)}
          >
            <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
          </button>
        </div>
      </div>
      {sourceOpen && source && (
        <div className="border-t border-border bg-secondary/35 px-4 py-4 sm:px-5">
          <p className="mb-1 text-xs font-semibold text-primary">
            {source.speaker ?? "Speaker"} · {formatDuration(source.start_ms)}
          </p>
          <blockquote className="font-serif leading-7">“{source.text}”</blockquote>
        </div>
      )}
      {background !== undefined && <BackgroundResearch value={background} />}
      {open && (
        <div className="grid gap-4 border-t border-border p-4 sm:grid-cols-2 sm:p-5">
          {Object.entries(action.extracted_fields)
            .filter(
              ([key, value]) =>
                !hiddenFieldKeys.has(key) &&
                !isPayloadOnlyFieldKey(key) &&
                !isReferenceFieldKey(key) &&
                shouldShowResultField(key, value),
            )
            .map(([key, value]) => (
              <label
                key={key}
                className={cn(
                  "text-xs font-semibold text-muted-foreground",
                  typeof value === "object" && "sm:col-span-2",
                )}
              >
                {humanizeFieldLabel(key)}
                {typeof value === "object" ? (
                  <Textarea
                    className="mt-2 min-h-24 bg-background text-sm leading-6 text-foreground"
                    value={displayValue(value)}
                    onChange={(event) =>
                      onFields({ ...action.extracted_fields, [key]: event.target.value })
                    }
                  />
                ) : (
                  <Input
                    className="mt-2 bg-background text-foreground"
                    value={displayValue(value)}
                    onChange={(event) =>
                      onFields({ ...action.extracted_fields, [key]: event.target.value })
                    }
                  />
                )}
              </label>
            ))}
          <ReferenceDetails
            className="sm:col-span-2"
            entries={Object.entries(action.extracted_fields).filter(
              ([key, value]) => !hiddenFieldKeys.has(key) && shouldShowReferenceField(key, value),
            )}
          />
        </div>
      )}
    </article>
  );
}

function AskComposer({
  sessionId,
  onResult,
}: {
  sessionId: string;
  onResult: (result: ActionResult) => void;
}) {
  const [instruction, setInstruction] = useState("");
  const catalogue = useQuery({ queryKey: ["models"], queryFn: hakiApi.listModels, retry: false });
  const [model, setModel] = useState("");
  const ask = useMutation({
    mutationFn: () =>
      hakiApi.ask(sessionId, { instruction: instruction.trim(), ...(model ? { model } : {}) }),
    onSuccess: (result) => {
      setInstruction("");
      onResult(result);
    },
  });
  const suggestions = [
    "Summarise this meeting for the partner in five bullet points.",
    "List every commitment my client made and its deadline.",
    "Draft talking points for the next mention.",
  ];
  return (
    <section className="chamber-card mt-8 rounded-lg border border-border p-4 sm:p-5">
      <div className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-3">
        <span className="grid size-11 place-items-center rounded-xl bg-secondary text-secondary-foreground">
          <Sparkles className="size-5" />
        </span>
        <div className="min-w-0">
          <h2 className="font-semibold text-foreground">Ask anything about this session</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Runs against the verified, non-redacted record only. Locked lines are never sent.
          </p>
        </div>
      </div>
      <Button asChild variant="outline" size="sm" className="mt-3">
        <Link to="/sessions/$sessionId/chat" params={{ sessionId }}>
          <MessageSquare className="size-4" /> Open chat — have a full conversation with your chosen
          model
        </Link>
      </Button>
      <Textarea
        aria-label="Instruction for this session"
        className="mt-4 min-h-24 bg-background"
        placeholder="e.g. List every deadline agreed on the record"
        value={instruction}
        onChange={(event) => setInstruction(event.target.value)}
      />
      <div className="mt-2 flex flex-wrap gap-2">
        {suggestions.map((item) => (
          <button
            key={item}
            type="button"
            className="min-h-9 rounded-full border border-border px-3 py-1 text-left text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground"
            onClick={() => setInstruction(item)}
          >
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
            <option value="">
              {catalogue.data ? `Default (${catalogue.data.default})` : "Default"}
            </option>
            {catalogue.data?.models.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <Button
          className="h-11 w-full sm:w-auto sm:self-end"
          disabled={!instruction.trim() || ask.isPending}
          onClick={() => ask.mutate()}
        >
          {ask.isPending ? "Working…" : "Run on this session"}
        </Button>
      </div>
      {catalogue.data?.configured === false && (
        <p className="mt-3 text-xs text-muted-foreground">
          No language model is connected yet, so answers will explain that instead of guessing. Add
          OPENROUTER_API_KEY or connect OpenRouter in{" "}
          <Link
            to="/settings"
            className="font-medium text-foreground underline-offset-4 hover:underline"
          >
            Settings
          </Link>
          .
        </p>
      )}
      {ask.error && (
        <p className="mt-3 text-sm text-destructive">{friendlyErrorMessage(ask.error)}</p>
      )}
    </section>
  );
}

function LegalIntelligence({
  sessionId,
  matterId,
  matters,
}: {
  sessionId?: string | undefined;
  matterId?: string | undefined;
  matters?: Matter[];
}) {
  const [filter, setFilter] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const activeMatterId = matterId || matters?.[0]?.id;
  const canGround = Boolean(sessionId || activeMatterId || (matters && matters.length));
  const intel = useQuery({
    queryKey: ["legal-intel", sessionId, activeMatterId],
    queryFn: () => hakiApi.listLegalIntel({ session_id: sessionId, matter_id: activeMatterId }),
    enabled: hasApiConfiguration,
    retry: false,
    refetchInterval: 15_000,
  });
  const retrieve = useMutation({
    mutationFn: () =>
      hakiApi.searchLegalIntel({ session_id: sessionId, matter_id: activeMatterId }),
    onSuccess: (data) => {
      if (data.grounded) {
        toast.success(
          data.hits.length
            ? `Retrieved ${data.hits.length} authorities connected to this record`
            : "No connected authorities matched this matter or transcript",
        );
      } else {
        toast.message(data.reason || "Legal search needs a matter or transcript");
      }
      void intel.refetch();
    },
    onError: (error) => toast.error(friendlyErrorMessage(error)),
  });
  const watch = useMutation({
    mutationFn: () => hakiApi.watchLegalIntel({ session_id: sessionId, matter_id: activeMatterId }),
    onSuccess: (data) => {
      if (!data.grounded) {
        toast.message(data.reason || "Legal intelligence needs a matter or transcript");
      } else if (data.monitor?.status === "local-only") {
        toast.message(
          "Watch saved locally — Exa did not register a monitor. Check EXA_API_KEY and the public webhook URL.",
        );
      } else if (data.created) {
        toast.success("Watching legal developments for this matter");
      } else {
        toast.success("Legal watch refreshed");
      }
      void intel.refetch();
    },
    onError: (error) => toast.error(friendlyErrorMessage(error)),
  });
  const retrievedHits = retrieve.data?.hits ?? watch.data?.hits;
  const hits = retrievedHits ?? intel.data?.hits ?? [];
  const scope = retrieve.data?.scope ?? watch.data?.scope;
  const reason = retrieve.data?.reason ?? watch.data?.reason;
  const label =
    scope?.matter_name || matters?.[0]?.matter_name || (sessionId ? "this record" : "open matters");
  const visibleHits = hits
    .filter((hit) =>
      `${hit.title ?? ""} ${hit.extract ?? ""} ${hit.connection?.join(" ") ?? ""} ${hit.matter_name ?? ""}`
        .toLowerCase()
        .includes(filter.trim().toLowerCase()),
    )
    .slice(0, 8);
  const monitorCount = intel.data?.monitors.length ?? 0;

  const sourceName = (hit: NewsHit) => {
    if (!hit.url) return "Source unavailable";
    try {
      return new URL(hit.url).hostname.replace(/^www\./, "");
    } catch {
      return "External source";
    }
  };

  const toggleExpanded = (key: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <section className="mt-10 overflow-hidden rounded-lg border border-intelligence-border bg-intelligence text-intelligence-foreground shadow-desk font-interface">
      <div className="border-b border-intelligence-border px-5 py-5 sm:px-6 sm:py-6">
        <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
          <div className="min-w-0">
            <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-intelligence-accent">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-intelligence-accent animate-live-dot" />
              Legal search & intelligence
            </div>
            <h2 className="truncate font-editorial text-2xl font-semibold sm:text-3xl">
              Authorities connected to the matter
            </h2>
            <p className="mt-2 max-w-2xl text-xs leading-5 text-intelligence-muted sm:text-sm">
              Exa only retrieves statutes, cases and legal developments that match a matter or the
              verified transcript. Unrelated web news is dropped.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:flex sm:shrink-0 sm:flex-wrap">
            <Button
              variant="outline"
              size="sm"
              className="min-w-0 border-intelligence-border bg-intelligence-panel px-2 text-intelligence-foreground hover:bg-intelligence-hover hover:text-intelligence-foreground sm:px-3"
              onClick={() => retrieve.mutate()}
              disabled={retrieve.isPending || !hasApiConfiguration || !canGround}
            >
              <BookOpen />{" "}
              <span className="hidden sm:inline">
                {retrieve.isPending ? "Retrieving…" : `Retrieve for ${label.slice(0, 28)}`}
              </span>
              <span className="sm:hidden">{retrieve.isPending ? "Retrieving…" : "Retrieve"}</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="min-w-0 text-intelligence-foreground hover:bg-intelligence-hover hover:text-intelligence-foreground"
              onClick={() => watch.mutate()}
              disabled={watch.isPending || !hasApiConfiguration || !canGround}
            >
              {watch.isPending ? "Watching…" : "Watch"}
            </Button>
          </div>
        </div>

        {scope?.terms?.length ? (
          <p className="mt-4 text-xs text-intelligence-muted">
            Grounded in {scope.has_transcript ? "transcript + " : ""}
            {scope.matter_name ? `matter “${scope.matter_name}”` : "this session"}
            {": "}
            {scope.terms.slice(0, 8).join(" · ")}
          </p>
        ) : null}

        <div className="mt-5 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
          <label className="relative block min-w-0">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-intelligence-muted" />
            <input
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              placeholder="Filter authorities and connection reasons"
              className="h-10 w-full rounded-md border border-intelligence-border bg-intelligence-panel pl-10 pr-3 text-sm text-intelligence-foreground outline-none placeholder:text-intelligence-muted focus:ring-1 focus:ring-intelligence-accent"
            />
          </label>
          <div className="flex items-center gap-4 text-[10px] font-medium uppercase tracking-[0.1em] text-intelligence-muted">
            <span>{hits.length} authorities</span>
            <span>
              {monitorCount} {monitorCount === 1 ? "watch" : "watches"}
            </span>
          </div>
        </div>
      </div>

      {!canGround && (
        <div className="px-5 py-12 text-center sm:px-6">
          <BookOpen className="mx-auto size-5 text-intelligence-muted" />
          <p className="mt-3 text-sm text-intelligence-muted">
            Open a session or generate a matter first. Legal intelligence will not search the open
            web on its own.
          </p>
        </div>
      )}

      {canGround && !hits.length && (
        <div className="px-5 py-12 text-center sm:px-6">
          <BookOpen className="mx-auto size-5 text-intelligence-muted" />
          <p className="mt-3 text-sm text-intelligence-muted">
            {reason ||
              "No connected authorities yet. Retrieve to search from this matter or transcript."}
          </p>
        </div>
      )}

      {!!hits.length && !visibleHits.length && (
        <p className="px-5 py-12 text-center text-sm text-intelligence-muted sm:px-6">
          No authorities match this filter.
        </p>
      )}

      <ol className="grid md:grid-cols-2 xl:grid-cols-3">
        {visibleHits.map((hit: NewsHit, index) => {
          const key = hit.id ?? hit.url ?? String(index);
          const isExpanded = expanded.has(key);
          return (
            <li
              key={key}
              className="group flex min-w-0 flex-col border-b border-intelligence-border p-5 md:border-r md:p-6 xl:[&:nth-child(3n)]:border-r-0"
            >
              <div className="flex items-center justify-between gap-3 text-[10px] font-medium uppercase tracking-[0.1em] text-intelligence-muted">
                <span className="rounded border border-intelligence-accent/30 bg-intelligence-accent/10 px-2 py-1 text-intelligence-accent">
                  {hit.kind || "Authority"}
                </span>
                <time dateTime={hit.published ?? undefined}>
                  {hit.published?.slice(0, 10) ?? "Date unavailable"}
                </time>
              </div>

              <h3 className="mt-4 font-editorial text-lg font-semibold leading-6 sm:text-xl">
                {hit.url ? (
                  <a
                    href={hit.url}
                    target="_blank"
                    rel="noreferrer"
                    className="transition-colors hover:text-intelligence-accent focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-intelligence-accent"
                  >
                    {hit.title ?? hit.url}
                  </a>
                ) : (
                  (hit.title ?? "Untitled authority")
                )}
              </h3>

              {hit.connection?.length ? (
                <p className="mt-2 text-xs leading-5 text-intelligence-accent">
                  {hit.connection.join(" · ")}
                </p>
              ) : null}

              {hit.extract && (
                <div className="mt-3 flex-1">
                  <p
                    className={cn(
                      "text-xs leading-5 text-intelligence-muted sm:text-sm sm:leading-6",
                      !isExpanded && "line-clamp-3",
                    )}
                  >
                    {hit.extract}
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-2 h-7 px-0 text-xs text-intelligence-accent hover:bg-transparent hover:text-intelligence-foreground"
                    onClick={() => toggleExpanded(key)}
                  >
                    {isExpanded ? "Show less" : "Read summary"}{" "}
                    <ChevronDown
                      className={cn("transition-transform", isExpanded && "rotate-180")}
                    />
                  </Button>
                </div>
              )}

              <div className="mt-5 grid grid-cols-[minmax(0,1fr)_auto] items-end gap-3 border-t border-intelligence-border pt-4">
                <div className="min-w-0">
                  <span className="block text-[9px] font-medium uppercase tracking-[0.12em] text-intelligence-muted">
                    Source
                  </span>
                  <span className="mt-1 block truncate text-xs font-medium">{sourceName(hit)}</span>
                </div>
                {hit.url && (
                  <a
                    href={hit.url}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`Open ${hit.title ?? "source"}`}
                    className="grid size-8 shrink-0 place-items-center rounded-md border border-intelligence-border text-intelligence-muted transition-colors hover:bg-intelligence-hover hover:text-intelligence-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-intelligence-accent"
                  >
                    <ExternalLink className="size-3.5" />
                  </a>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      <div className="grid gap-2 border-t border-intelligence-border px-5 py-4 text-[10px] uppercase tracking-[0.1em] text-intelligence-muted sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:px-6">
        <span className="flex min-w-0 items-center gap-2">
          <ShieldCheck className="size-3.5 shrink-0 text-intelligence-accent" /> Background
          reference only — verify before relying on it.
        </span>
        <span>Connected authorities only</span>
      </div>
    </section>
  );
}

function BackgroundResearch({ value }: { value: unknown }) {
  const [expanded, setExpanded] = useState(false);
  const sources = parseBackgroundInfo(value);
  if (!sources.length) return null;
  return (
    <div className="border-t border-border bg-muted/40 px-4 py-4 sm:px-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        External research — not from the record
      </p>
      <ul className="mt-3 space-y-4">
        {sources.map((source, index) => {
          const host = sourceHostname(source.url);
          const extract = source.extract ?? "";
          const facts = source.facts ?? [];
          const long = extract.length > 280 || extract.split("\n").length > 4 || facts.length > 4;
          return (
            <li
              key={`${source.url ?? source.title ?? index}`}
              className="rounded-lg border border-border/70 bg-card/80 p-3 sm:p-4"
            >
              {source.url ? (
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex max-w-full items-start gap-1.5 break-words font-medium text-primary hover:underline"
                >
                  {source.title ?? host ?? source.url}
                  <ExternalLink className="mt-0.5 size-3.5 shrink-0" />
                </a>
              ) : (
                <p className="font-medium text-foreground">
                  {source.title ?? "Open-web background"}
                </p>
              )}
              {(host || source.published) && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {[host, source.published ? displayValue(source.published) : null]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              )}
              {extract && (
                <p
                  className={cn(
                    "mt-2 whitespace-pre-wrap text-sm leading-6 text-foreground/85",
                    !expanded && "line-clamp-4",
                  )}
                >
                  {extract}
                </p>
              )}
              {!!facts.length && (
                <ul
                  className={cn(
                    "mt-3 space-y-1.5 border-t border-border/60 pt-3 text-sm leading-6 text-foreground/85",
                    !expanded && facts.length > 4 && "max-h-28 overflow-hidden",
                  )}
                >
                  {(expanded ? facts : facts.slice(0, 4)).map((fact) => (
                    <li key={fact} className="grid grid-cols-[auto_minmax(0,1fr)] gap-2">
                      <span
                        className="mt-2 size-1.5 shrink-0 rounded-full bg-primary/70"
                        aria-hidden
                      />
                      <span>{fact}</span>
                    </li>
                  ))}
                </ul>
              )}
              {long && (
                <button
                  type="button"
                  className="mt-3 text-xs font-semibold text-primary hover:underline"
                  onClick={() => setExpanded((current) => !current)}
                >
                  {expanded ? "Show less" : "Read summary"}
                </button>
              )}
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-[11px] leading-5 text-muted-foreground">
        Verify this source before relying on it in filed work.
      </p>
    </div>
  );
}

function SourceList({ sources }: { sources: ResearchSource[] }) {
  if (!sources.length) return null;
  return (
    <ol className="mt-5 space-y-3 border-t border-border pt-4">
      {sources.map((source, index) => (
        <li key={`${source.url ?? index}`} className="text-sm">
          <span className="mr-2 text-xs font-semibold text-muted-foreground">{index + 1}.</span>
          {source.url ? (
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="break-words font-medium text-primary hover:underline"
            >
              {source.title ?? sourceHostname(source.url) ?? "Open source"}
            </a>
          ) : (
            <span className="font-medium">{source.title ?? "Untitled source"}</span>
          )}
          {source.citation && (
            <span className="ml-2 text-xs text-muted-foreground">{source.citation}</span>
          )}
          {source.kind && (
            <Badge variant="outline" className="ml-2 capitalize">
              {source.kind}
            </Badge>
          )}
          {source.published && (
            <span className="ml-2 text-xs text-muted-foreground">
              {displayValue(source.published)}
            </span>
          )}
          {source.extract && (
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{source.extract}</p>
          )}
        </li>
      ))}
    </ol>
  );
}

function ResultsList({ results, sessionId }: { results: ActionResult[]; sessionId: string }) {
  const [filter, setFilter] = useState<"all" | "ready" | "failed">("all");
  const readyCount = results.filter((item) => item.status !== "error").length;
  const failedCount = results.length - readyCount;
  const visible = results.filter((item) => {
    if (filter === "ready") return item.status !== "error";
    if (filter === "failed") return item.status === "error";
    return true;
  });

  return (
    <div className="mt-6 sm:mt-8">
      <div className="mb-5 flex flex-col gap-4 rounded-2xl border border-border bg-card/70 p-4 sm:mb-6 sm:flex-row sm:items-center sm:justify-between sm:p-5">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
            Review desk
          </p>
          <p className="mt-1 font-serif text-xl font-semibold leading-snug sm:text-2xl">
            {readyCount} ready{failedCount > 0 ? ` · ${failedCount} needs attention` : ""}
          </p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Edit drafts here before anything leaves the workspace.
          </p>
        </div>
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter results">
          {(
            [
              { id: "all", label: `All (${results.length})` },
              { id: "ready", label: `Ready (${readyCount})` },
              ...(failedCount > 0
                ? [{ id: "failed" as const, label: `Failed (${failedCount})` }]
                : []),
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={filter === item.id}
              className={cn(
                "min-h-10 rounded-full border px-3.5 py-2 text-sm font-medium transition-colors",
                filter === item.id
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-background text-muted-foreground hover:border-primary/40 hover:text-foreground",
              )}
              onClick={() => setFilter(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4 sm:space-y-5">
        {visible.map((item, index) => (
          <ResultCard key={item.action_id} result={item} sessionId={sessionId} index={index} />
        ))}
      </div>

      {!visible.length && (
        <div className="chamber-card rounded-2xl border border-dashed border-border py-12 text-center">
          <p className="font-serif text-xl font-semibold">Nothing in this filter</p>
          <p className="mt-2 text-sm text-muted-foreground">
            Switch filters to see the rest of the generated work.
          </p>
        </div>
      )}
    </div>
  );
}

function ResultMeta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0 rounded-xl border border-border/70 bg-background/70 px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </p>
      <div className="mt-1.5 text-sm leading-6 text-foreground">{children}</div>
    </div>
  );
}

function ReferenceDetails({
  entries,
  className,
}: {
  entries: [string, unknown][];
  className?: string;
}) {
  if (!entries.length) return null;
  return (
    <div
      className={cn(
        "rounded-xl border border-dashed border-border/80 bg-muted/20 px-4 py-3",
        className,
      )}
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        System references
      </p>
      <ul className="mt-3 space-y-3">
        {entries.map(([key, value]) => {
          const full = String(value ?? "").trim();
          return (
            <li
              key={key}
              className="min-w-0 rounded-lg border border-border/60 bg-background/60 px-3 py-2.5"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[11px] font-medium text-muted-foreground">
                    {humanizeFieldLabel(key)}
                  </p>
                  <p className="mt-1 break-all text-sm leading-5 text-foreground/85">
                    {full || "—"}
                  </p>
                </div>
                {full && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 shrink-0 px-2 text-xs"
                    onClick={() => {
                      void navigator.clipboard.writeText(full);
                      toast.success("Reference copied");
                    }}
                  >
                    <Copy className="size-3.5" /> Copy
                  </Button>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function ResultActions({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] sm:flex-wrap sm:overflow-visible sm:pb-0">
      {children}
    </div>
  );
}

function ResultCard({
  result,
  sessionId,
}: {
  result: ActionResult;
  sessionId: string;
  index?: number;
}) {
  const Icon = actionIcons[result.type];
  const [documentText, setDocumentText] = useState(
    displayValue(result.result["document_text"] ?? ""),
  );
  const queryClient = useQueryClient();
  const storageProviders = useQuery({
    queryKey: ["integrations"],
    queryFn: hakiApi.listIntegrations,
    select: (items) =>
      items.filter(
        (item) =>
          item.group === "storage" && item.connected && item.provider_id !== "google_calendar",
      ),
    retry: false,
  });
  const calendarProvider = useQuery({
    queryKey: ["integrations"],
    queryFn: hakiApi.listIntegrations,
    select: (items) =>
      items.find((item) => item.provider_id === "google_calendar" && item.connected) ?? null,
    retry: false,
  });
  const [exportOpen, setExportOpen] = useState(false);
  const exportDoc = useMutation({
    mutationFn: ({ provider }: { provider: string }) =>
      hakiApi.exportDocument(sessionId, result.action_id, provider),
    onSuccess: (data) => {
      toast.success(
        data.url ? `Exported to ${data.provider}` : `Export queued for ${data.provider}`,
      );
      queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
      setExportOpen(false);
    },
    onError: (error: Error) => {
      if (reauthProvider(error)) {
        toast.error(error.message, {
          action: {
            label: "Reconnect",
            onClick: () => {
              window.location.href = "/settings?section=connectors";
            },
          },
          duration: 10000,
        });
        return;
      }
      toast.error(
        friendlyErrorMessage(error, "Export failed. Check the storage connector and try again."),
      );
    },
  });

  const typeLabel = result.type.replaceAll("_", " ");
  const savedExternally = Object.keys(result.result).some((key) =>
    [
      "document_id",
      "ambiguous_document_id",
      "calendar_id",
      "ambiguous_event_id",
      "contact_id",
      "matter_id",
      "workspace_url",
    ].includes(key),
  );
  const statusNote = friendlyStatusNote(result.result["note"]);

  if (result.status === "error") {
    return (
      <article className="chamber-card overflow-hidden rounded-2xl border border-destructive/30 bg-card">
        <div className="flex items-start gap-3 border-b border-destructive/15 bg-destructive/5 px-4 py-4 sm:px-6">
          <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-destructive/10 text-destructive">
            <AlertCircle className="size-5" />
          </span>
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-destructive">
              Needs attention
            </p>
            <h2 className="mt-1 font-serif text-xl font-semibold capitalize">{typeLabel}</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {friendlyErrorMessage(result.error, "The service returned an error for this item.")}
            </p>
          </div>
        </div>
        <div className="px-4 py-3 text-xs text-muted-foreground sm:px-6">
          Use Retry failed below, or return to Actions and generate this item again.
        </div>
      </article>
    );
  }

  const calendarHref =
    typeof result.result["ics"] === "string"
      ? `data:text/calendar;charset=utf-8,${encodeURIComponent(result.result["ics"])}`
      : null;
  const workspaceUrl =
    typeof result.result["workspace_url"] === "string" ? result.result["workspace_url"] : null;
  const shareUrl =
    typeof result.result["whatsapp_share_url"] === "string"
      ? result.result["whatsapp_share_url"]
      : whatsappShareUrl(
          documentText ||
            displayValue(
              result.result["note_text"] ??
                result.result["narrative"] ??
                result.result["description"] ??
                result.result["matter_name"] ??
                result.type,
            ),
        );
  const visibleMeta = Object.entries(result.result).filter(([key, value]) => {
    if (key === "note" && statusNote) return false;
    return shouldShowResultField(key, value);
  });
  const referenceEntries = Object.entries(result.result).filter(([key, value]) =>
    shouldShowReferenceField(key, value),
  );
  const title =
    result.type === "workspace_matter"
      ? `${result.result["note"] ? (String(result.result["note"]).startsWith("linked") ? "Linked matter" : "New matter") : "Matter"}: ${displayValue(result.result["matter_name"])}`
      : result.type === "crm_entry"
        ? `Contact: ${displayValue(result.result["contact_name"])}`
        : result.type === "private_note"
          ? "Private note"
          : result.type === "time_entry"
            ? `${formatBillableHours(result.result["duration_hours"])} · ${displayValue(result.result["matter_name"] ?? "This session")}`
            : result.type === "draft_document"
              ? "Editable legal draft"
              : typeLabel;
  const longText =
    result.type === "time_entry"
      ? displayValue(result.result["narrative"] ?? result.result["activity_description"] ?? "")
      : result.type === "calendar_event"
        ? displayValue(result.result["description"] ?? "")
        : result.type === "private_note"
          ? displayValue(result.result["note_text"] ?? "")
          : "";

  return (
    <article className="chamber-card overflow-hidden rounded-2xl border border-border">
      <header className="grid gap-4 border-b border-border bg-gradient-to-br from-success/40 via-card to-card px-4 py-4 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center sm:px-6 sm:py-5">
        <span className="grid size-12 place-items-center rounded-2xl bg-success text-success-foreground shadow-sm">
          <Icon className="size-5" />
        </span>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant="secondary"
              className="border-success-foreground/15 bg-success/70 text-success-foreground"
            >
              Ready to review
            </Badge>
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              {typeLabel}
            </span>
          </div>
          <h2 className="mt-2 break-words font-serif text-xl font-semibold leading-snug capitalize sm:text-2xl">
            {title}
          </h2>
        </div>
        <div className="hidden text-right text-xs text-muted-foreground sm:block">
          {savedExternally ? "In library + tools" : "Local result"}
        </div>
      </header>

      {result.type === "draft_document" ? (
        <div className="p-4 sm:p-6 lg:p-8">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-muted-foreground">
              Edit freely. Nothing is filed until you export or share.
            </p>
            <ResultActions>
              <Button
                variant="outline"
                size="sm"
                className="h-10 shrink-0"
                onClick={() => {
                  void navigator.clipboard.writeText(documentText);
                  toast.success("Draft copied");
                }}
              >
                <Copy /> Copy
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-10 shrink-0"
                onClick={() => {
                  downloadTextFile("hakiscribe-draft.txt", documentText);
                  toast.success("Draft downloaded");
                }}
              >
                <Download /> Download
              </Button>
              <Button asChild variant="outline" size="sm" className="h-10 shrink-0">
                <a href={shareUrl} target="_blank" rel="noreferrer">
                  <MessageCircle /> WhatsApp
                </a>
              </Button>
              {(workspaceUrl || typeof result.result["ambiguous_document_url"] === "string") && (
                <Button asChild variant="outline" size="sm" className="h-10 shrink-0">
                  <a
                    href={(workspaceUrl || result.result["ambiguous_document_url"]) as string}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <FileText /> Ambiguous
                  </a>
                </Button>
              )}
              {storageProviders.data && storageProviders.data.length > 0 && (
                <div className="relative shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-10"
                    onClick={() => setExportOpen((prev) => !prev)}
                  >
                    <ExternalLink /> Export
                  </Button>
                  {exportOpen && (
                    <div className="absolute right-0 z-10 mt-1 min-w-48 rounded-xl border border-border bg-popover p-1.5 shadow-lg">
                      {storageProviders.data.map((provider) => (
                        <button
                          key={provider.provider_id}
                          type="button"
                          disabled={exportDoc.isPending}
                          onClick={() => exportDoc.mutate({ provider: provider.provider_id })}
                          className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm hover:bg-accent disabled:opacity-50"
                        >
                          <Cloud className="size-3.5" />
                          {provider.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </ResultActions>
          </div>
          <div className="overflow-hidden rounded-2xl border border-border bg-background shadow-[inset_0_1px_0_oklch(1_0_0/0.65)]">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground sm:px-6">
              <span>Draft document</span>
              <span>Editable</span>
            </div>
            <Textarea
              aria-label="Editable legal document"
              value={documentText}
              onChange={(event) => setDocumentText(event.target.value)}
              className="min-h-[22rem] resize-y rounded-none border-0 bg-transparent p-5 font-serif text-base leading-8 shadow-none focus-visible:ring-0 sm:min-h-[28rem] sm:p-8 lg:p-10"
            />
          </div>
        </div>
      ) : result.type === "legal_research" || result.type === "web_search" ? (
        <div className="space-y-5 p-4 sm:p-6">
          <ResultMeta
            label={result.type === "legal_research" ? "Question researched" : "Background check"}
          >
            <p className="font-serif text-lg leading-7">
              {displayValue(result.result["question"])}
            </p>
          </ResultMeta>
          <div className="rounded-2xl border border-border bg-background/80 p-4 sm:p-5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Answer
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-7">
              {displayValue(result.result["answer"])}
            </p>
          </div>
          <SourceList sources={(result.result["sources"] as ResearchSource[] | undefined) ?? []} />
          <p className="text-xs leading-5 text-muted-foreground">
            {result.type === "legal_research"
              ? "Check every authority before relying on it. Research is never merged into a draft."
              : "Background reference only. Never used as evidence or as a drafted fact."}
          </p>
        </div>
      ) : result.type === "llm_task" ? (
        <div className="space-y-5 p-4 sm:p-6">
          <ResultMeta label="Instruction">
            <p>{displayValue(result.result["instruction"])}</p>
          </ResultMeta>
          <div className="rounded-2xl border border-border bg-background/80 p-4 sm:p-5">
            <p className="whitespace-pre-wrap font-serif text-base leading-7">
              {displayValue(result.result["output"])}
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            {typeof result.result["model"] === "string" && result.result["model"] && (
              <Badge variant="outline">
                Prepared with {friendlyModelName(result.result["model"])}
              </Badge>
            )}
            <Button
              variant="outline"
              size="sm"
              className="h-10"
              onClick={() =>
                void navigator.clipboard.writeText(displayValue(result.result["output"]))
              }
            >
              <Copy /> Copy
            </Button>
          </div>
        </div>
      ) : result.type === "private_note" ? (
        <div className="p-4 sm:p-6 lg:p-8">
          <div className="rounded-2xl border border-border bg-background/80 p-5 sm:p-7">
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Private to you
            </p>
            <p className="mt-3 whitespace-pre-wrap font-serif text-base leading-8">{longText}</p>
          </div>
        </div>
      ) : result.type === "time_entry" ? (
        <div className="space-y-4 p-4 sm:p-6">
          <div className="grid gap-3 sm:grid-cols-3">
            <ResultMeta label="Hours">
              <p className="font-serif text-3xl font-semibold">
                {formatBillableHours(result.result["duration_hours"])}
              </p>
            </ResultMeta>
            <ResultMeta label="Matter">
              <p>{displayValue(result.result["matter_name"])}</p>
            </ResultMeta>
            <ResultMeta label="Billable">
              <p>{displayValue(result.result["billable"] ?? true)}</p>
            </ResultMeta>
          </div>
          <div className="rounded-2xl border border-border bg-background/80 p-4 sm:p-5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Narrative
            </p>
            <p className="mt-2 whitespace-pre-wrap font-serif text-base leading-7">{longText}</p>
          </div>
        </div>
      ) : (
        <div className="space-y-4 p-4 sm:p-6">
          {!!visibleMeta.length && (
            <div className="grid gap-3 sm:grid-cols-2">
              {visibleMeta.map(([key, value]) => (
                <ResultMeta key={key} label={humanizeFieldLabel(key)}>
                  <p className="whitespace-pre-wrap">
                    {key === "duration_hours" ? formatBillableHours(value) : displayValue(value)}
                  </p>
                </ResultMeta>
              ))}
            </div>
          )}
          {statusNote && (
            <p className="rounded-xl border border-border/70 bg-background/70 px-4 py-3 text-sm leading-6 text-muted-foreground">
              {statusNote}
            </p>
          )}
          {longText && result.type === "calendar_event" && (
            <div className="rounded-2xl border border-border bg-background/80 p-4 sm:p-5">
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                Description
              </p>
              <p className="mt-2 whitespace-pre-wrap font-serif text-base leading-7">{longText}</p>
            </div>
          )}
          <ResultActions>
            {calendarHref && (
              <Button asChild variant="outline" className="h-10 shrink-0">
                <a href={calendarHref} download="hakiscribe-event.ics">
                  <Download /> Download calendar file
                </a>
              </Button>
            )}
            {calendarProvider.data && (
              <Button
                variant="outline"
                className="h-10 shrink-0"
                disabled={exportDoc.isPending}
                onClick={() => exportDoc.mutate({ provider: "google_calendar" })}
              >
                <CalendarPlus /> Google Calendar
              </Button>
            )}
            <Button asChild variant="outline" className="h-10 shrink-0">
              <a href={shareUrl} target="_blank" rel="noreferrer">
                <MessageCircle /> WhatsApp
              </a>
            </Button>
            {workspaceUrl && (
              <Button asChild variant="outline" className="h-10 shrink-0">
                <a href={workspaceUrl} target="_blank" rel="noreferrer">
                  Open in Ambiguous
                </a>
              </Button>
            )}
          </ResultActions>
        </div>
      )}

      <footer className="grid gap-3 border-t border-border bg-muted/30 px-4 py-3.5 text-xs text-muted-foreground sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:px-6">
        <span className="inline-flex items-start gap-2 leading-5">
          <ShieldCheck className="mt-0.5 size-3.5 shrink-0 text-primary" />
          {savedExternally
            ? "Saved to the Session Library and connected tools"
            : "Saved as a local HakiScribe result until you export"}
        </span>
        {result.type !== "draft_document" &&
          result.type !== "calendar_event" &&
          result.type !== "workspace_matter" &&
          result.type !== "crm_entry" && (
            <Button
              asChild
              variant="ghost"
              size="sm"
              className="h-9 justify-self-start px-2 text-xs sm:justify-self-end"
            >
              <a href={shareUrl} target="_blank" rel="noreferrer">
                <MessageCircle className="size-3.5" /> WhatsApp
              </a>
            </Button>
          )}
      </footer>
      {!!referenceEntries.length && (
        <div className="border-t border-border px-4 py-3 sm:px-6">
          <ReferenceDetails entries={referenceEntries} />
        </div>
      )}
    </article>
  );
}
