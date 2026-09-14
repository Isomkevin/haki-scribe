import { useEffect, useState, type ComponentType, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  BriefcaseBusiness,
  Info,
  LockKeyhole,
  Plug,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  apiBaseUrl,
  friendlyErrorMessage,
  hakiApi,
  hasApiConfiguration,
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
import { ConnectorsSection } from "./connectors";
import { InstallAppButton } from "./pwa-register";
import { PageShell, WorkspaceFooter } from "./shell";
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
        copy="These details stay in this browser. HakiScribe does not use a login yet, so the profile is workspace configuration rather than an account."
      />
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
    </section>
  );
}

function WorkspaceSection() {
  const { settings, commit } = useStoredSettings();

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
      <p className="mt-6 text-xs leading-5 text-muted-foreground">
        Timezone for dates on the record is Africa/Nairobi. Session titles, transcripts, and generated work remain in
        the private workspace, not in these settings.
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
