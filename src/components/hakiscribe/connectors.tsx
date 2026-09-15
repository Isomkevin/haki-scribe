import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  CheckCircle2,
  Copy,
  ExternalLink,
  Headphones,
  Link2,
  Loader2,
  LockKeyhole,
  Plug,
  RefreshCw,
  ShieldCheck,
  Unplug,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  friendlyErrorMessage,
  hakiApi,
  omiMiniappUrls,
  startIntegrationOAuth,
  type Integration,
  type IntegrationField,
  type OmiStatus,
} from "@/lib/hakiscribe";
import { SectionHeading } from "./shell";

const GROUP_LABELS: Record<string, string> = {
  ai: "AI assistants",
  storage: "Cloud storage",
  practice: "Practice suite",
};

export function ConnectorsSection() {
  const queryClient = useQueryClient();
  const integrations = useQuery({
    queryKey: ["integrations"],
    queryFn: hakiApi.listIntegrations,
    retry: false,
  });
  const omiStatus = useQuery({
    queryKey: ["omi-status"],
    queryFn: hakiApi.omiStatus,
    retry: false,
  });

  const [dialogProvider, setDialogProvider] = useState<Integration | null>(null);
  const [dialogValues, setDialogValues] = useState<Record<string, string>>({});
  const [dialogError, setDialogError] = useState<string | null>(null);
  const [omiDialogOpen, setOmiDialogOpen] = useState(false);
  const [oauthPending, setOauthPending] = useState<string | null>(null);
  const [manualUid, setManualUid] = useState("");

  const connect = useMutation({
    mutationFn: ({ providerId, credentials }: { providerId: string; credentials: Record<string, string> }) =>
      hakiApi.connectIntegration(providerId, credentials),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["integrations"] });
      void queryClient.invalidateQueries({ queryKey: ["models"] });
      void queryClient.invalidateQueries({ queryKey: ["omi-status"] });
      void queryClient.invalidateQueries({ queryKey: ["health"] });
      setDialogProvider(null);
      setOmiDialogOpen(false);
      setDialogValues({});
      setManualUid("");
      setDialogError(null);
      toast.success("Connector linked");
    },
    onError: (error: Error) => {
      setDialogError(friendlyErrorMessage(error, "Could not verify that connector. Check the key and try again."));
    },
  });

  const disconnect = useMutation({
    mutationFn: (providerId: string) => hakiApi.disconnectIntegration(providerId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["integrations"] });
      void queryClient.invalidateQueries({ queryKey: ["models"] });
      void queryClient.invalidateQueries({ queryKey: ["omi-status"] });
      void queryClient.invalidateQueries({ queryKey: ["health"] });
      toast.success("Connector disconnected");
    },
  });

  const grouped: Record<string, Integration[]> = {};
  for (const item of integrations.data ?? []) {
    const group = item.group;
    if (!grouped[group]) grouped[group] = [];
    grouped[group].push(item);
  }

  const connectedCount = (integrations.data ?? []).filter((item) => item.connected).length;

  async function beginOAuth(provider: Integration, params?: Record<string, string>) {
    setOauthPending(provider.provider_id);
    setDialogProvider(null);
    setDialogValues({});
    try {
      const outcome = await startIntegrationOAuth(provider.provider_id, params);
      if (outcome === "connected") {
        toast.success(`${provider.name} connected`);
      } else {
        toast.error(`${provider.name} sign-in was not completed.`);
      }
    } catch (error) {
      toast.error(friendlyErrorMessage(error, `Could not open the ${provider.name} sign-in window.`));
    } finally {
      setOauthPending(null);
      void queryClient.invalidateQueries({ queryKey: ["integrations"] });
      void queryClient.invalidateQueries({ queryKey: ["health"] });
    }
  }

  function openConnect(provider: Integration) {
    if (provider.oauth && provider.oauth_configured) {
      // Some sign-ins need a detail first (e.g. the Google Cloud project for Gemini).
      if ((provider.fields ?? []).length > 0) {
        setDialogProvider(provider);
        setDialogValues({});
        setDialogError(null);
        return;
      }
      void beginOAuth(provider);
      return;
    }
    if (provider.provider_id === "omi") {
      setOmiDialogOpen(true);
      setDialogError(null);
      setManualUid("");
      return;
    }
    setDialogProvider(provider);
    setDialogValues({});
    setDialogError(null);
  }

  function submitConnect() {
    if (!dialogProvider) return;
    if (dialogProvider.oauth && dialogProvider.oauth_configured) {
      const required = (dialogProvider.fields ?? [])[0];
      if (required && !(dialogValues[required.id] ?? "").trim()) {
        setDialogError(`${required.label} is needed before signing in.`);
        return;
      }
      void beginOAuth(dialogProvider, dialogValues);
      return;
    }
    connect.mutate({ providerId: dialogProvider.provider_id, credentials: dialogValues });
  }

  function submitManualOmiUid() {
    const uid = manualUid.trim();
    if (!uid) {
      setDialogError("Paste the Omi uid from the Auth URL or Developer tools.");
      return;
    }
    connect.mutate({ providerId: "omi", credentials: { uid } });
  }

  return (
    <div id="connectors">
      <header className="mb-7">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Connectors</p>
            <h2 className="mt-2 max-w-3xl font-serif text-2xl font-semibold leading-tight sm:text-3xl">
              Link HakiScribe to the tools your practice already uses
            </h2>
          </div>
          <Badge variant="outline" className="gap-1.5">
            <Plug className="size-3" />
            {connectedCount} connected
          </Badge>
        </div>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
          Connect your own AI keys, cloud storage, Omi wearable and practice suite so drafted documents, research and
          calendar events flow to where your work lives. Credentials are stored on the server — never in the browser.
        </p>
      </header>

      {integrations.isError ? (
        <div className="mb-6 rounded-lg border border-destructive/30 bg-destructive/5 p-4 sm:p-5">
          <p className="font-medium text-destructive">Connectors could not load</p>
          <p className="mt-1 text-sm leading-6 text-destructive/90">
            {friendlyErrorMessage(
              integrations.error,
              "Connectors are unavailable right now. Confirm the HakiScribe backend is running, then try again.",
            )}
          </p>
          <Button type="button" variant="outline" size="sm" className="mt-4" onClick={() => void integrations.refetch()}>
            <RefreshCw className="size-3.5" />
            Try again
          </Button>
        </div>
      ) : null}

      {integrations.isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-lg border border-border bg-card" />
          ))}
        </div>
      ) : null}

      {Object.entries(grouped).map(([group, providers]) => (
        <section key={group} className="mb-9">
          <SectionHeading eyebrow={GROUP_LABELS[group] ?? group} title={GROUP_LABELS[group] ?? group} />
          <div className="grid gap-4 sm:grid-cols-2">
            {providers.map((provider) =>
              provider.provider_id === "omi" ? (
                <OmiProviderCard
                  key={provider.provider_id}
                  provider={provider}
                  status={omiStatus.data}
                  onOpen={() => openConnect(provider)}
                  onDisconnect={() => disconnect.mutate(provider.provider_id)}
                  isDisconnecting={disconnect.isPending && disconnect.variables === provider.provider_id}
                />
              ) : (
                <ProviderCard
                  key={provider.provider_id}
                  provider={provider}
                  onConnect={() => openConnect(provider)}
                  onDisconnect={() => disconnect.mutate(provider.provider_id)}
                  isConnecting={oauthPending === provider.provider_id}
                  isDisconnecting={disconnect.isPending && disconnect.variables === provider.provider_id}
                />
              ),
            )}
          </div>
        </section>
      ))}

      <section className="mb-2 rounded-lg border border-border/70 bg-muted/30 p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <LockKeyhole className="mt-0.5 size-4 shrink-0 text-primary" />
          <div className="min-w-0 text-xs leading-5 text-muted-foreground">
            <p className="font-medium text-foreground">How connectors reach the transcript</p>
            <p className="mt-1">
              AI providers extend the "Ask an AI model" task — they receive the assembled prompt and the verified,
              non-redacted transcript slice, never a session ID or direct database access. Intron Sahara transcribes
              full recordings on Stop for multilingual sessions (legal court-hearing mode). Storage providers receive the
              already-generated document text, not the raw record. Omi posts transcripts to the webhook after Miniapp
              auth links your uid. All calls run server-side; the browser only shows progress and results.
            </p>
          </div>
        </div>
      </section>

      <Dialog open={dialogProvider !== null} onOpenChange={(open) => !open && setDialogProvider(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-serif">Connect {dialogProvider?.name}</DialogTitle>
            <DialogDescription>{dialogProvider?.what_it_does}</DialogDescription>
          </DialogHeader>
          {dialogProvider?.fields.map((field: IntegrationField) => (
            <div key={field.id} className="grid gap-1.5">
              <label className="text-sm font-medium">{field.label}</label>
              <input
                type={field.type}
                placeholder={field.placeholder}
                value={dialogValues[field.id] ?? ""}
                onChange={(e) => setDialogValues((prev) => ({ ...prev, [field.id]: e.target.value }))}
                className="rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                autoComplete="off"
              />
              <p className="text-xs text-muted-foreground">{field.help}</p>
            </div>
          ))}
          {dialogError ? (
            <p className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{dialogError}</p>
          ) : null}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogProvider(null)}>
              Cancel
            </Button>
            <Button onClick={submitConnect} disabled={connect.isPending}>
              {connect.isPending ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" /> Verifying…
                </>
              ) : (
                "Connect"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <OmiSetupDialog
        open={omiDialogOpen}
        status={omiStatus.data}
        manualUid={manualUid}
        onManualUid={setManualUid}
        error={dialogError}
        connecting={connect.isPending}
        onClose={() => setOmiDialogOpen(false)}
        onLinkManual={submitManualOmiUid}
      />
    </div>
  );
}

function copyText(label: string, value: string) {
  void navigator.clipboard.writeText(value);
  toast.success(`${label} copied`);
}

function OmiSetupDialog({
  open,
  status,
  manualUid,
  onManualUid,
  error,
  connecting,
  onClose,
  onLinkManual,
}: {
  open: boolean;
  status?: OmiStatus | undefined;
  manualUid: string;
  onManualUid: (value: string) => void;
  error: string | null;
  connecting: boolean;
  onClose: () => void;
  onLinkManual: () => void;
}) {
  const urls = status
    ? {
        webhookUrl: status.webhook_url,
        authUrl: status.auth_url,
        setupCompletedUrl: status.setup_completed_url,
      }
    : omiMiniappUrls();

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-serif">Connect Omi wearable</DialogTitle>
          <DialogDescription>
            Install a private HakiScribe integration app in Omi. Auth links your uid once — no per-session webhook paste.
          </DialogDescription>
        </DialogHeader>
        <ol className="list-decimal space-y-2 pl-5 text-sm leading-6 text-muted-foreground">
          <li>In Omi: Explore → Create an App → External integration.</li>
          <li>Paste the webhook URL. Prefer Real-time transcript; point Memory creation at the same URL when allowed.</li>
          <li>Set Auth URL and Setup completed URL below.</li>
          <li>Install the app and open Auth — HakiScribe will mark Omi connected.</li>
        </ol>
        <div className="space-y-3">
          <UrlRow label="Webhook URL" value={urls.webhookUrl} />
          <UrlRow label="Auth URL" value={urls.authUrl} openable />
          <UrlRow label="Setup completed URL" value={urls.setupCompletedUrl} />
        </div>
        <div className="rounded-lg border border-border bg-muted/30 p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Local / dev link</p>
          <p className="mt-1 text-xs text-muted-foreground">Paste an Omi uid to link without the mobile Auth flow.</p>
          <input
            className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
            placeholder="omi-user-…"
            value={manualUid}
            onChange={(e) => onManualUid(e.target.value)}
            autoComplete="off"
          />
          <Button className="mt-2" size="sm" onClick={onLinkManual} disabled={connecting}>
            {connecting ? <Loader2 className="mr-2 size-3.5 animate-spin" /> : <Link2 className="mr-2 size-3.5" />}
            Link uid
          </Button>
        </div>
        {error ? (
          <p className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</p>
        ) : null}
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function UrlRow({ label, value, openable }: { label: string; value: string; openable?: boolean }) {
  return (
    <div className="rounded-md border border-border bg-background p-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">{label}</p>
      <p className="mt-1 break-all font-mono text-[11px] text-foreground">{value}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button type="button" size="sm" variant="outline" onClick={() => copyText(label, value)}>
          <Copy className="mr-1.5 size-3.5" />
          Copy
        </Button>
        {openable ? (
          <Button type="button" size="sm" variant="outline" asChild>
            <a href={value} target="_blank" rel="noreferrer">
              <ExternalLink className="mr-1.5 size-3.5" />
              Open
            </a>
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function OmiProviderCard({
  provider,
  status,
  onOpen,
  onDisconnect,
  isDisconnecting,
}: {
  provider: Integration;
  status?: OmiStatus | undefined;
  onOpen: () => void;
  onDisconnect: () => void;
  isDisconnecting: boolean;
}) {
  const linked = provider.connected || Boolean(status?.linked);
  const masked = status?.masked_uid || provider.masked_creds?.['uid'];

  return (
    <div className="flex flex-col rounded-lg border border-border bg-card p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-2 font-serif text-base font-semibold">
            <Headphones className="size-4 text-primary" />
            {provider.name}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{provider.what_it_does}</p>
        </div>
        {linked ? (
          <Badge variant="outline" className="shrink-0 gap-1 border-success-foreground/20 bg-success/10 text-success-foreground">
            <CheckCircle2 className="size-3" />
            Connected
          </Badge>
        ) : (
          <Badge variant="secondary" className="shrink-0">
            Not connected
          </Badge>
        )}
      </div>

      {provider.capabilities.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {provider.capabilities.map((cap) => (
            <span key={cap} className="rounded-md border border-border/70 bg-muted/40 px-2 py-1 text-[11px] text-muted-foreground">
              {cap}
            </span>
          ))}
        </div>
      ) : null}

      {linked && masked ? (
        <p className="mt-3 text-[11px] text-muted-foreground">
          Linked uid {masked}
          {status?.last_activity_at
            ? ` · last activity ${new Date(status.last_activity_at).toLocaleString("en-KE", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}`
            : ""}
        </p>
      ) : (
        <p className="mt-3 text-[11px] text-muted-foreground">Install the Miniapp once, then speak — sessions appear on the desk.</p>
      )}

      <div className="mt-auto flex flex-wrap gap-2 pt-4">
        <Button size="sm" variant={linked ? "outline" : "default"} onClick={onOpen}>
          <Link2 className="mr-2 size-3.5" />
          {linked ? "Miniapp URLs" : "Connect"}
        </Button>
        {linked ? (
          <Button variant="outline" size="sm" onClick={onDisconnect} disabled={isDisconnecting}>
            {isDisconnecting ? <Loader2 className="mr-2 size-3.5 animate-spin" /> : <Unplug className="mr-2 size-3.5" />}
            Disconnect
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function ProviderCard({
  provider,
  onConnect,
  onDisconnect,
  isConnecting,
  isDisconnecting,
}: {
  provider: Integration;
  onConnect: () => void;
  onDisconnect: () => void;
  isConnecting: boolean;
  isDisconnecting: boolean;
}) {
  const signInLabel = provider.oauth
    ? provider.provider_id === "dropbox"
      ? "Sign in with Dropbox"
      : provider.provider_id === "onedrive"
        ? "Sign in with Microsoft"
        : "Sign in with Google"
    : "Connect";
  const needsSetup = Boolean(provider.oauth) && !provider.oauth_configured;

  return (
    <div className="flex flex-col rounded-lg border border-border bg-card p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-2 font-serif text-base font-semibold">{provider.name}</p>
          <p className="mt-1 text-xs text-muted-foreground">{provider.what_it_does}</p>
        </div>
        {provider.connected ? (
          <Badge variant="outline" className="shrink-0 gap-1 border-success-foreground/20 bg-success/10 text-success-foreground">
            <CheckCircle2 className="size-3" />
            {provider.source === "workspace" ? "Workspace key" : "Connected"}
          </Badge>
        ) : (
          <Badge variant="secondary" className="shrink-0">
            Not connected
          </Badge>
        )}
      </div>

      {provider.capabilities.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {provider.capabilities.map((cap) => (
            <span key={cap} className="rounded-md border border-border/70 bg-muted/40 px-2 py-1 text-[11px] text-muted-foreground">
              {cap}
            </span>
          ))}
        </div>
      ) : null}

      {provider.connected && provider.source === "workspace" ? (
        <p className="mt-3 text-[11px] text-muted-foreground">
          Using the workspace {provider.name} key from server config. Ask routes through this connector.
        </p>
      ) : null}
      {provider.connected && provider.account ? (
        <p className="mt-3 flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <ShieldCheck className="size-3 text-primary" />
          Signed in as {provider.account}
        </p>
      ) : null}
      {needsSetup ? (
        <p className="mt-3 text-[11px] leading-5 text-muted-foreground">
          Sign-in is not switched on for this service yet. Add the app credentials on the server, using the redirect
          address <span className="break-all font-mono">{provider.oauth_setup?.redirect_uri}</span>. You can still paste
          a token manually below.
        </p>
      ) : null}
      {provider.connected && provider.connected_at ? (
        <p className="mt-3 text-[11px] text-muted-foreground">
          Connected{" "}
          {new Date(provider.connected_at).toLocaleDateString("en-KE", { day: "numeric", month: "short", year: "numeric" })}
        </p>
      ) : null}

      <div className="mt-auto pt-4">
        {provider.connected && provider.source === "workspace" ? (
          <Button size="sm" variant="outline" onClick={onConnect}>
            <Link2 className="mr-2 size-3.5" />
            Replace key
          </Button>
        ) : provider.connected ? (
          <div className="flex flex-wrap gap-2">
            {provider.oauth && provider.oauth_configured ? (
              <Button size="sm" variant="outline" onClick={onConnect} disabled={isConnecting}>
                {isConnecting ? <Loader2 className="mr-2 size-3.5 animate-spin" /> : <RefreshCw className="mr-2 size-3.5" />}
                Reconnect
              </Button>
            ) : null}
            <Button variant="outline" size="sm" onClick={onDisconnect} disabled={isDisconnecting}>
              {isDisconnecting ? <Loader2 className="mr-2 size-3.5 animate-spin" /> : <Unplug className="mr-2 size-3.5" />}
              Disconnect
            </Button>
          </div>
        ) : (
          <Button size="sm" onClick={onConnect} disabled={isConnecting}>
            {isConnecting ? <Loader2 className="mr-2 size-3.5 animate-spin" /> : <Link2 className="mr-2 size-3.5" />}
            {signInLabel}
          </Button>
        )}
      </div>
    </div>
  );
}
