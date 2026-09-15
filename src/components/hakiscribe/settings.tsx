import { useEffect, useState, type ComponentType, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  BriefcaseBusiness,
  History,
  Info,
  KeyRound,
  LockKeyhole,
  Plug,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { useDemoMode } from "@/hooks/use-demo-mode";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import {
  apiBaseUrl,
  friendlyErrorMessage,
  hakiApi,
  hasApiConfiguration,
  type Integration,
  type Session,
  type SessionSource,
} from "@/lib/hakiscribe";
import {
  LANGUAGE_OPTIONS,
  PRACTICE_ROLES,
  defaultWorkspaceSettings,
  loadWorkspaceSettings,
  saveWorkspaceSettings,
  type SettingsSection,
  type WorkspaceProfile,
  type WorkspaceSettings,
} from "@/lib/workspace-settings";
import { filterDemoSessions } from "@/lib/demo-mode";
import { ConnectorsSection } from "./connectors";
import { InstallAppButton } from "./pwa-register";
import { PageShell, SourceIcon, StatusBadge, WorkspaceFooter } from "./shell";
import { TrustLine } from "./brand";

const NAV: { id: SettingsSection; label: string; icon: ComponentType<{ className?: string }> }[] = [
  { id: "profile", label: "Profile", icon: UserRound },
  { id: "workspace", label: "Workspace", icon: BriefcaseBusiness },
  { id: "security", label: "Security", icon: ShieldCheck },
  { id: "connectors", label: "Connectors", icon: Plug },
  { id: "about", label: "About", icon: Info },
];

export function SettingsPage({ section }: { section: SettingsSection }) {
  return (
    <PageShell back>
      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-10">
        <header className="mb-7 border-b border-border pb-7 sm:mb-8 sm:pb-8">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Settings</p>
          <h1 className="mt-2 max-w-3xl font-serif text-3xl font-semibold leading-tight sm:text-4xl">
            Workspace settings
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
            Profile, security, and the connectors your practice uses. Client sessions stay in the private workspace.
          </p>
          <TrustLine className="mt-4" />
        </header>

        <div className="grid gap-8 lg:grid-cols-[13.5rem_minmax(0,1fr)] lg:items-start lg:gap-10">
          <nav aria-label="Settings sections" className="flex gap-2 overflow-x-auto lg:sticky lg:top-24 lg:block lg:overflow-visible">
            <p className="mb-2 hidden text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground lg:block">
              This workspace
            </p>
            {NAV.map(({ id, label, icon: Icon }) => (
              <Link
                key={id}
                to="/settings"
                search={{ section: id }}
                className={cn(
                  "inline-flex shrink-0 items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium lg:mb-1 lg:flex lg:w-full",
                  section === id
                    ? "border-primary/20 bg-secondary text-secondary-foreground"
                    : "border-transparent text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <Icon className="size-4 text-primary" />
                {label}
              </Link>
            ))}
          </nav>

          {section === "profile" && <ProfileSection />}
          {section === "workspace" && <WorkspaceSection />}
          {section === "security" && <SecuritySection />}
          {section === "connectors" && <ConnectorsSection />}
          {section === "about" && <AboutSection />}
        </div>
      </main>
      <WorkspaceFooter />
    </PageShell>
  );
}

function useStoredSettings() {
  const [settings, setSettings] = useState<WorkspaceSettings>(defaultWorkspaceSettings);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setSettings(loadWorkspaceSettings());
    setLoaded(true);
  }, []);

  function commit(next: WorkspaceSettings) {
    setSettings(next);
    saveWorkspaceSettings(next);
  }

  return { settings, loaded, commit };
}

function fieldClassName() {
  return "mt-2 h-11 bg-background";
}

function ProfileSection() {
  const { settings, loaded, commit } = useStoredSettings();
  const { session: authSession } = useAuth();
  const [draft, setDraft] = useState<WorkspaceProfile>(settings.profile);

  useEffect(() => {
    if (loaded) setDraft(settings.profile);
  }, [loaded, settings.profile]);

  function save() {
    commit({ ...settings, profile: draft });
    toast.success("Profile saved on this device.");
  }

  return (
    <section>
      <SectionIntro
        eyebrow="Profile"
        title="How this practice is identified on this device"
        copy="Local display details for this browser, plus linked views of connectors, masked keys, and recent private sessions."
      />
      {authSession?.user && (
        <div className="mb-6 rounded-lg border border-border bg-card px-4 py-3 sm:px-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Signed in</p>
          <p className="mt-1 font-medium text-foreground">
            {authSession.user.name || authSession.user.email}
          </p>
          {authSession.user.email && authSession.user.name ? (
            <p className="mt-0.5 text-sm text-muted-foreground">{authSession.user.email}</p>
          ) : null}
        </div>
      )}
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Full name" htmlFor="display-name">
          <Input
            id="display-name"
            className={fieldClassName()}
            value={draft.displayName}
            onChange={(event) => setDraft((current) => ({ ...current, displayName: event.target.value }))}
            placeholder="e.g. Amina Otieno"
          />
        </Field>
        <Field label="Practice or chambers" htmlFor="practice-name">
          <Input
            id="practice-name"
            className={fieldClassName()}
            value={draft.practiceName}
            onChange={(event) => setDraft((current) => ({ ...current, practiceName: event.target.value }))}
            placeholder="e.g. Otieno & Company Advocates"
          />
        </Field>
        <Field label="Email" htmlFor="profile-email">
          <Input
            id="profile-email"
            type="email"
            className={fieldClassName()}
            value={draft.email}
            onChange={(event) => setDraft((current) => ({ ...current, email: event.target.value }))}
            placeholder="chambers@example.co.ke"
          />
        </Field>
        <Field label="Role" htmlFor="profile-role">
          <select
            id="profile-role"
            value={draft.role}
            onChange={(event) => setDraft((current) => ({ ...current, role: event.target.value }))}
            className="mt-2 h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
          >
            {PRACTICE_ROLES.map((role) => (
              <option key={role.id} value={role.id}>
                {role.label}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Button className="mt-6" onClick={save}>
        Save profile
      </Button>

      <ProfileLinkedOverview />
    </section>
  );
}

const RECENT_SESSION_LIMIT = 5;

function ProfileLinkedOverview() {
  const { enabled: demoDataEnabled } = useDemoMode();
  const integrations = useQuery({
    queryKey: ["integrations"],
    queryFn: hakiApi.listIntegrations,
    enabled: hasApiConfiguration,
    retry: false,
  });
  const sessions = useQuery({
    queryKey: ["sessions", { includeDemo: demoDataEnabled }],
    queryFn: () => hakiApi.listSessions({ includeDemo: demoDataEnabled }),
    enabled: hasApiConfiguration,
    retry: false,
  });

  const connected = (integrations.data ?? []).filter((item) => item.connected);
  const recent = filterDemoSessions(sessions.data ?? [], demoDataEnabled)
    .slice()
    .sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime())
    .slice(0, RECENT_SESSION_LIMIT);

  return (
    <div className="mt-10 space-y-8 border-t border-border pt-8">
      <div>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Connected tools</p>
            <h3 className="mt-1 font-serif text-xl font-semibold">Integrations and keys</h3>
            <p className="mt-1 max-w-xl text-sm leading-6 text-muted-foreground">
              Linked connectors and masked credentials. Manage connect or disconnect from Connectors.
            </p>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to="/settings" search={{ section: "connectors" }}>
              Manage connectors
              <ArrowRight className="size-3.5" />
            </Link>
          </Button>
        </div>

        {!hasApiConfiguration && (
          <EmptyLinkedState message="Add VITE_API_BASE_URL to load connectors and keys from the workspace service." />
        )}
        {hasApiConfiguration && integrations.isLoading && (
          <div className="space-y-2">
            {[1, 2].map((i) => (
              <div key={i} className="h-16 animate-pulse rounded-lg border border-border bg-card" />
            ))}
          </div>
        )}
        {hasApiConfiguration && integrations.isError && (
          <EmptyLinkedState
            message={friendlyErrorMessage(integrations.error, "Could not load connectors.")}
            action={
              <Button type="button" variant="outline" size="sm" onClick={() => void integrations.refetch()}>
                Try again
              </Button>
            }
          />
        )}
        {hasApiConfiguration && integrations.data && connected.length === 0 && (
          <EmptyLinkedState
            message="No connectors linked yet."
            action={
              <Button asChild variant="outline" size="sm">
                <Link to="/settings" search={{ section: "connectors" }}>
                  <Plug className="size-3.5" />
                  Open connectors
                </Link>
              </Button>
            }
          />
        )}
        {connected.length > 0 && (
          <ul className="space-y-2">
            {connected.map((provider) => (
              <ConnectedIntegrationRow key={provider.provider_id} provider={provider} />
            ))}
          </ul>
        )}
      </div>

      <div>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Session history</p>
            <h3 className="mt-1 font-serif text-xl font-semibold">Recent private sessions</h3>
            <p className="mt-1 max-w-xl text-sm leading-6 text-muted-foreground">
              Open a session workspace, or browse the full library.
            </p>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to="/new">
              Full library
              <ArrowRight className="size-3.5" />
            </Link>
          </Button>
        </div>

        {!hasApiConfiguration && (
          <EmptyLinkedState message="Add VITE_API_BASE_URL to load session history from the workspace service." />
        )}
        {hasApiConfiguration && sessions.isLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg border border-border bg-card" />
            ))}
          </div>
        )}
        {hasApiConfiguration && sessions.isError && (
          <EmptyLinkedState
            message={friendlyErrorMessage(sessions.error, "Could not load sessions.")}
            action={
              <Button type="button" variant="outline" size="sm" onClick={() => void sessions.refetch()}>
                Try again
              </Button>
            }
          />
        )}
        {hasApiConfiguration && sessions.data && recent.length === 0 && (
          <EmptyLinkedState
            message="No sessions yet."
            action={
              <Button asChild variant="outline" size="sm">
                <Link to="/new">
                  <History className="size-3.5" />
                  Start a session
                </Link>
              </Button>
            }
          />
        )}
        {recent.length > 0 && (
          <ul className="space-y-2">
            {recent.map((session) => (
              <ProfileSessionRow key={session.id} session={session} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function ConnectedIntegrationRow({ provider }: { provider: Integration }) {
  const credEntries = Object.entries(provider.masked_creds ?? {}).filter(([, value]) => Boolean(value));
  const sourceLabel =
    provider.source === "workspace" ? "Workspace key" : provider.account ? `Signed in as ${provider.account}` : "Connected";

  return (
    <li>
      <Link
        to="/settings"
        search={{ section: "connectors" }}
        className="group flex items-start gap-3 rounded-lg border border-border bg-card px-4 py-3 transition-colors hover:border-primary/30 hover:bg-muted/40"
      >
        <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-md bg-secondary text-secondary-foreground">
          <Plug className="size-4 text-primary" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-medium text-foreground group-hover:text-primary">{provider.name}</span>
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              {provider.group}
            </span>
          </span>
          <span className="mt-0.5 block text-xs text-muted-foreground">{sourceLabel}</span>
          {credEntries.length > 0 ? (
            <span className="mt-2 flex flex-wrap gap-2">
              {credEntries.map(([field, value]) => (
                <span
                  key={field}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2 py-1 font-mono text-[11px] text-muted-foreground"
                >
                  <KeyRound className="size-3 shrink-0 text-primary" />
                  <span className="capitalize">{field.replaceAll("_", " ")}</span>
                  <span className="text-foreground/80">{value}</span>
                </span>
              ))}
            </span>
          ) : provider.connected ? (
            <span className="mt-2 inline-flex items-center gap-1.5 text-xs text-muted-foreground">
              <KeyRound className="size-3 text-primary" />
              {provider.oauth || provider.auth === "oauth" ? "OAuth linked · no API key stored in browser" : "Key stored server-side"}
            </span>
          ) : null}
          {provider.connected_at ? (
            <span className="mt-1.5 block text-[11px] text-muted-foreground">
              Linked{" "}
              {new Date(provider.connected_at).toLocaleDateString(undefined, {
                day: "numeric",
                month: "short",
                year: "numeric",
              })}
            </span>
          ) : null}
        </span>
        <ArrowRight className="mt-2 size-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
      </Link>
    </li>
  );
}

function ProfileSessionRow({ session }: { session: Session }) {
  return (
    <li>
      <Link
        to="/sessions/$sessionId"
        params={{ sessionId: session.id }}
        search={{ fresh: false }}
        className="group flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 transition-colors hover:border-primary/30 hover:bg-muted/40"
      >
        <span className="grid size-9 shrink-0 place-items-center rounded-md bg-secondary text-secondary-foreground">
          <SourceIcon source={session.source} className="size-4" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium text-foreground group-hover:text-primary">{session.title}</span>
          <span className="mt-0.5 block text-xs text-muted-foreground">
            {new Date(session.updated_at || session.created_at).toLocaleDateString(undefined, {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
            {" · "}
            {session.source === "omi" ? "Omi wearable" : "Microphone"}
          </span>
        </span>
        <StatusBadge status={session.status} />
        <ArrowRight className="size-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
      </Link>
    </li>
  );
}

function EmptyLinkedState({ message, action }: { message: string; action?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-muted/20 px-4 py-6 text-center">
      <p className="text-sm text-muted-foreground">{message}</p>
      {action ? <div className="mt-3 flex justify-center">{action}</div> : null}
    </div>
  );
}

function WorkspaceSection() {
  const { settings, commit } = useStoredSettings();
  const { enabled: demoEnabled, setEnabled: setDemoEnabled } = useDemoMode();
  const queryClient = useQueryClient();

  function onDemoToggle(next: boolean) {
    setDemoEnabled(next);
    commit({
      ...settings,
      workspace: { ...settings.workspace, useDemoData: next },
    });
    void queryClient.invalidateQueries({ queryKey: ["sessions"] });
    void queryClient.invalidateQueries({ queryKey: ["matters"] });
    void queryClient.invalidateQueries({ queryKey: ["contacts"] });
    toast.success(next ? "Demo data is on for this device." : "Demo data is off — showing only your live work.");
  }

  return (
    <section>
      <SectionIntro
        eyebrow="Workspace"
        title="Defaults for new private sessions"
        copy="Language and capture source apply the next time you open a session from the private workspace."
      />
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Default language" htmlFor="default-language">
          <select
            id="default-language"
            value={settings.workspace.defaultLanguage}
            onChange={(event) => {
              commit({
                ...settings,
                workspace: { ...settings.workspace, defaultLanguage: event.target.value },
              });
              toast.success("Default language updated.");
            }}
            className="mt-2 h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
          >
            {LANGUAGE_OPTIONS.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Default capture source" htmlFor="default-source">
          <select
            id="default-source"
            value={settings.workspace.defaultSource}
            onChange={(event) => {
              const defaultSource = event.target.value as SessionSource;
              commit({
                ...settings,
                workspace: { ...settings.workspace, defaultSource },
              });
              toast.success("Default capture source updated.");
            }}
            className="mt-2 h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="mic">Microphone</option>
            <option value="omi">Omi wearable</option>
          </select>
        </Field>
      </div>

      <div className="mt-8 rounded-xl border border-border bg-card/60 p-4 sm:p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <Label htmlFor="use-demo-data" className="text-sm font-semibold text-foreground">
              Use Demo Data
            </Label>
            <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
              When on, the library can restore seeded sample sessions and show judge-demo shortcuts.
              Turn off for day-to-day practice — seeded demos disappear from lists and dashboards;
              only sessions and matters you create remain visible.
            </p>
          </div>
          <Switch
            id="use-demo-data"
            checked={demoEnabled}
            onCheckedChange={onDemoToggle}
            aria-label="Use Demo Data"
            className="mt-1 shrink-0"
          />
        </div>
      </div>

      <p className="mt-6 text-xs leading-5 text-muted-foreground">
        Timezone for dates on the record is Africa/Nairobi. Session titles, transcripts, and generated work remain in
        the private workspace, not in these settings. This preference is stored on this device.
      </p>
    </section>
  );
}

function SecuritySection() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: hakiApi.health,
    enabled: hasApiConfiguration,
    retry: false,
  });
  const live = Object.entries(health.data?.integrations ?? {})
    .filter(([, on]) => on)
    .map(([name]) => name);

  return (
    <section>
      <SectionIntro
        eyebrow="Security"
        title="Privilege, credentials, and this deployment"
        copy="HakiScribe is a private listening workspace. There is no individual login yet, so treat this URL as confidential to the practice."
      />
      <ul className="space-y-4">
        <SecurityPoint
          title="Privilege before any model"
          body="Relabel speakers and lock privileged or off-record lines before detection. Hidden lines stay on the record for you and are excluded from analysis and generation."
        />
        <SecurityPoint
          title="Credentials stay on the server"
          body="Connector keys are stored server-side and masked in the browser. Connectors receive only the approved artifact or transcript slice they need — never a session ID or direct database access."
        />
        <SecurityPoint
          title="Not used to train foundation models"
          body="Live captions and analysis use your configured keys. Generated work stays local until you choose to send it to a connected tool."
        />
      </ul>
      <div className="mt-6 rounded-lg border border-border bg-card p-4 sm:p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Workspace service</p>
        <p className="mt-2 font-serif text-lg font-semibold">
          {hasApiConfiguration ? (health.data?.status === "ok" || health.data?.status ? "Connected" : health.isLoading ? "Checking…" : "Unreachable") : "Not configured"}
        </p>
        <p className="mt-1 break-all text-xs text-muted-foreground">
          {hasApiConfiguration ? apiBaseUrl : "Add VITE_API_BASE_URL to reach the HakiScribe service."}
        </p>
        {health.isError && (
          <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/5 p-3">
            <p className="text-sm font-medium text-destructive">Service check failed</p>
            <p className="mt-1 text-sm leading-5 text-destructive/90">
              {friendlyErrorMessage(
                health.error,
                "The workspace service could not be reached. Confirm it is running and that VITE_API_BASE_URL is correct.",
              )}
            </p>
          </div>
        )}
        {live.length > 0 && (
          <p className="mt-3 text-xs text-muted-foreground">Live integrations: {live.join(" · ")}</p>
        )}
      </div>
    </section>
  );
}

function AboutSection() {
  return (
    <section>
      <SectionIntro
        eyebrow="About"
        title="HakiScribe, a listening instrument of HakiChain"
        copy="A private companion for Kenyan legal rooms: capture what matters, protect privilege, then choose source-traceable work."
      />
      <dl className="grid gap-4 sm:grid-cols-2">
        <AboutItem term="Product" detail="HakiScribe" />
        <AboutItem term="Studio" detail="HakiChain · Nairobi" />
        <AboutItem term="Languages" detail="English · Kiswahili · code-switch" />
        <AboutItem term="Record" detail="Privilege stays in the room" />
      </dl>
      <p className="mt-6 max-w-2xl text-sm leading-6 text-muted-foreground">
        Session setup, transcripts, speaker review, and generated artifacts live in the private workspace. This settings
        page is for workspace configuration only.
      </p>
      <div className="mt-6 rounded-lg border border-border bg-card p-4">
        <p className="text-sm font-medium text-foreground">Install on this device</p>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">
          Add HakiScribe as an app for faster access in chambers. The offline shell never stores privileged records.
        </p>
        <div className="mt-3">
          <InstallAppButton />
        </div>
      </div>
      <div className="mt-6 flex flex-wrap gap-2">
        <Button asChild variant="outline">
          <Link to="/">Product landing</Link>
        </Button>
        <Button asChild>
          <Link to="/new">Open private workspace</Link>
        </Button>
      </div>
    </section>
  );
}

function SectionIntro({ eyebrow, title, copy }: { eyebrow: string; title: string; copy: string }) {
  return (
    <header className="mb-7">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">{eyebrow}</p>
      <h2 className="mt-2 max-w-3xl font-serif text-2xl font-semibold leading-tight sm:text-3xl">{title}</h2>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">{copy}</p>
    </header>
  );
}

function Field({ label, htmlFor, children }: { label: string; htmlFor: string; children: ReactNode }) {
  return (
    <div>
      <Label htmlFor={htmlFor} className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </Label>
      {children}
    </div>
  );
}

function SecurityPoint({ title, body }: { title: string; body: string }) {
  return (
    <li className="flex items-start gap-3 rounded-lg border border-border bg-card p-4">
      <LockKeyhole className="mt-0.5 size-4 shrink-0 text-primary" />
      <div className="min-w-0">
        <p className="font-medium text-foreground">{title}</p>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">{body}</p>
      </div>
    </li>
  );
}

function AboutItem({ term, detail }: { term: string; detail: string }) {
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3">
      <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{term}</dt>
      <dd className="mt-1 font-serif text-lg font-semibold">{detail}</dd>
    </div>
  );
}
