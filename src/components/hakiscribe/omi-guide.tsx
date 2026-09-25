import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { ArrowRight, CheckCircle2, Circle, Copy, Headphones, KeyRound, Radio } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { hakiApi, omiMiniappUrls } from "@/lib/hakiscribe";
import { PageShell } from "./shell";

function copy(label: string, value: string) {
  void navigator.clipboard?.writeText(value).then(
    () => toast.success(`${label} copied`),
    () => toast.error("Could not copy — select the text instead"),
  );
}

function Step({ n, done, title, children }: { n: number; done?: boolean; title: string; children: React.ReactNode }) {
  return (
    <li className="grid grid-cols-[auto_minmax(0,1fr)] gap-3">
      <span className={`grid size-8 place-items-center rounded-full border text-sm font-semibold ${done ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card text-muted-foreground"}`}>
        {done ? <CheckCircle2 className="size-4" /> : n}
      </span>
      <div className="min-w-0 pb-6">
        <h3 className="font-semibold text-foreground">{title}</h3>
        <div className="mt-1.5 space-y-2 text-sm leading-6 text-muted-foreground">{children}</div>
      </div>
    </li>
  );
}

function CopyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-border bg-background p-2">
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">{label}</p>
        <p className="truncate font-mono text-[11px] text-foreground">{value}</p>
      </div>
      <Button size="sm" variant="outline" onClick={() => copy(label, value)} aria-label={`Copy ${label}`}>
        <Copy className="size-3.5" />
      </Button>
    </div>
  );
}

export function OmiGuidePage() {
  const status = useQuery({ queryKey: ["omi-status"], queryFn: hakiApi.omiStatus, retry: false });
  const s = status.data;
  const urls = s
    ? { webhookUrl: s.webhook_url, authUrl: s.auth_url, setupCompletedUrl: s.setup_completed_url }
    : omiMiniappUrls();
  const appLinked = Boolean(s?.app_linked ?? s?.linked);
  const keySaved = Boolean(s?.api_key_connected);

  return (
    <PageShell back>
      <header className="mb-6">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">Connectors · Omi wearable</p>
        <h1 className="mt-1 flex items-center gap-2 font-serif text-2xl font-semibold sm:text-3xl">
          <Headphones className="size-6 text-primary" /> Set up your Omi
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Pair once and HakiScribe captures meetings from your pendant — live into an open session, or imported after the fact.
        </p>
        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${appLinked ? "border-primary/30 bg-primary/10 text-primary" : "border-border text-muted-foreground"}`}>
            {appLinked ? <CheckCircle2 className="size-3.5" /> : <Circle className="size-3.5" />} Live link {appLinked ? "active" : "not set up"}
          </span>
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${keySaved ? "border-primary/30 bg-primary/10 text-primary" : "border-border text-muted-foreground"}`}>
            {keySaved ? <CheckCircle2 className="size-3.5" /> : <Circle className="size-3.5" />} Developer key {keySaved ? "saved" : "not added"}
          </span>
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="rounded-lg border border-border bg-card p-5">
          <h2 className="flex items-center gap-2 font-serif text-lg font-semibold"><Radio className="size-4 text-primary" /> Live transcription</h2>
          <p className="mt-1 mb-5 text-xs text-muted-foreground">Recommended. Words appear in your session as you speak.</p>
          <ol>
            <Step n={1} title="Create the app in Omi">
              <p>In the Omi phone app: Explore → Create an App → External integration.</p>
            </Step>
            <Step n={2} title="Paste these three links">
              <p>Choose "Real-time transcript" as the trigger.</p>
              <CopyRow label="Webhook URL" value={urls.webhookUrl} />
              <CopyRow label="Auth URL" value={urls.authUrl} />
              <CopyRow label="Setup completed URL" value={urls.setupCompletedUrl} />
            </Step>
            <Step n={3} done={appLinked} title="Install and open Auth">
              <p>Install your app in Omi and tap its Auth link. This page updates to "Live link active".</p>
            </Step>
            <Step n={4} title="Record a session">
              <p>Start a new session and choose Omi as the source. Transcripts go straight into that session.</p>
              <Button asChild size="sm" variant="outline"><Link to="/new">Start a session <ArrowRight className="size-3.5" /></Link></Button>
            </Step>
          </ol>
        </section>

        <section className="rounded-lg border border-border bg-card p-5">
          <h2 className="flex items-center gap-2 font-serif text-lg font-semibold"><KeyRound className="size-4 text-primary" /> Import past conversations</h2>
          <p className="mt-1 mb-5 text-xs text-muted-foreground">Optional. Bring in meetings Omi already captured.</p>
          <ol>
            <Step n={1} title="Create a developer key">
              <p>In the Omi app: Settings → Developer → Create key. Copy it.</p>
            </Step>
            <Step n={2} done={keySaved} title="Save it on the Omi card">
              <p>Open the Omi card, tap Setup and paste the key. HakiScribe checks it with Omi straight away.</p>
            </Step>
            <Step n={3} title="Import">
              <p>Tap "Import from Omi" on the card. Each conversation becomes a session you can review.</p>
            </Step>
          </ol>
          <div className="rounded-md border border-border bg-muted/40 p-3 text-xs leading-5 text-muted-foreground">
            Privileged or off-record lines can still be locked before anything is analysed.
          </div>
        </section>
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        <Button asChild>
          <Link to="/settings" search={{ section: "connectors", q: "omi" }}>Go to the Omi card <ArrowRight className="size-4" /></Link>
        </Button>
        <Button variant="outline" onClick={() => void status.refetch()} disabled={status.isFetching}>Refresh status</Button>
      </div>
    </PageShell>
  );
}
