import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  CheckCircle2,
  Link2,
  Loader2,
  LockKeyhole,
  Plug,
  Unplug,
} from "lucide-react";
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
import { hakiApi, type Integration, type IntegrationField } from "@/lib/hakiscribe";
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

  const [dialogProvider, setDialogProvider] = useState<Integration | null>(null);
  const [dialogValues, setDialogValues] = useState<Record<string, string>>({});
  const [dialogError, setDialogError] = useState<string | null>(null);

  const connect = useMutation({
    mutationFn: ({ providerId, credentials }: { providerId: string; credentials: Record<string, string> }) =>
      hakiApi.connectIntegration(providerId, credentials),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      queryClient.invalidateQueries({ queryKey: ["models"] });
      setDialogProvider(null);
      setDialogValues({});
      setDialogError(null);
    },
    onError: (error: Error) => {
      setDialogError(error instanceof Error ? error.message : "Could not connect.");
    },
  });

  const disconnect = useMutation({
    mutationFn: (providerId: string) => hakiApi.disconnectIntegration(providerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      queryClient.invalidateQueries({ queryKey: ["models"] });
    },
  });

  const grouped: Record<string, Integration[]> = {};
  for (const item of integrations.data ?? []) {
    const group = item.group;
    if (!grouped[group]) grouped[group] = [];
    grouped[group].push(item);
  }

  const connectedCount = (integrations.data ?? []).filter((item) => item.connected).length;

  function openConnect(provider: Integration) {
    setDialogProvider(provider);
    setDialogValues({});
    setDialogError(null);
  }

  function submitConnect() {
    if (!dialogProvider) return;
    connect.mutate({ providerId: dialogProvider.provider_id, credentials: dialogValues });
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
            Connect your own AI keys, cloud storage and practice suite so drafted documents, research and calendar
            events flow to where your work lives. Credentials are stored on the server — never in the browser.
          </p>
        </header>

        {integrations.isError ? (
          <p className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            {integrations.error instanceof Error ? integrations.error.message : "Could not load connectors."}
          </p>
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
              {providers.map((provider) => (
                <ProviderCard
                  key={provider.provider_id}
                  provider={provider}
                  onConnect={() => openConnect(provider)}
                  onDisconnect={() => disconnect.mutate(provider.provider_id)}
                  isDisconnecting={disconnect.isPending && disconnect.variables === provider.provider_id}
                />
              ))}
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
                non-redacted transcript slice, never a session ID or direct database access. Storage providers receive
                the already-generated document text, not the raw record. All calls run server-side; the browser only
                shows progress and results.
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
            <p className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              {dialogError}
            </p>
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
    </div>
  );
}

function ProviderCard({
  provider,
  onConnect,
  onDisconnect,
  isDisconnecting,
}: {
  provider: Integration;
  onConnect: () => void;
  onDisconnect: () => void;
  isDisconnecting: boolean;
}) {
  return (
    <div className="flex flex-col rounded-lg border border-border bg-card p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-2 font-serif text-base font-semibold">
            {provider.name}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{provider.what_it_does}</p>
        </div>
        {provider.connected ? (
          <Badge variant="outline" className="shrink-0 gap-1 border-success-foreground/20 bg-success/10 text-success-foreground">
            <CheckCircle2 className="size-3" />
            {provider.source === "workspace" ? "Workspace key" : "Connected"}
          </Badge>
        ) : (
          <Badge variant="secondary" className="shrink-0">Not connected</Badge>
        )}
      </div>

      {provider.capabilities.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {provider.capabilities.map((cap) => (
            <span
              key={cap}
              className="rounded-md border border-border/70 bg-muted/40 px-2 py-1 text-[11px] text-muted-foreground"
            >
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
      {provider.connected && provider.connected_at ? (
        <p className="mt-3 text-[11px] text-muted-foreground">
          Connected {new Date(provider.connected_at).toLocaleDateString("en-KE", { day: "numeric", month: "short", year: "numeric" })}
        </p>
      ) : null}

      <div className="mt-auto pt-4">
        {provider.connected && provider.source === "workspace" ? (
          <Button size="sm" variant="outline" onClick={onConnect}>
            <Link2 className="mr-2 size-3.5" />
            Replace key
          </Button>
        ) : provider.connected ? (
          <Button variant="outline" size="sm" onClick={onDisconnect} disabled={isDisconnecting}>
            {isDisconnecting ? (
              <Loader2 className="mr-2 size-3.5 animate-spin" />
            ) : (
              <Unplug className="mr-2 size-3.5" />
            )}
            Disconnect
          </Button>
        ) : (
          <Button size="sm" onClick={onConnect}>
            <Link2 className="mr-2 size-3.5" />
            Connect
          </Button>
        )}
      </div>
    </div>
  );
}
