import { Plug } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ConnectorsSection } from "./connectors";
import { PageShell, WorkspaceFooter } from "./shell";
import { TrustLine } from "./brand";

export function SettingsPage() {
  return (
    <PageShell back>
      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-10">
        <header className="mb-7 border-b border-border pb-7 sm:mb-8 sm:pb-8">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Settings</p>
          <h1 className="mt-2 max-w-3xl font-serif text-3xl font-semibold leading-tight sm:text-4xl">
            Configure the workspace, then keep client work on the record
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
            Connectors live here because they are workspace configuration: your own keys, storage, and practice tools.
            Credentials stay on the server. Sessions never see them.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Badge variant="outline" className="gap-1.5">
              <Plug className="size-3" />
              Workspace configuration
            </Badge>
            <TrustLine />
          </div>
        </header>

        <div className="grid gap-8 lg:grid-cols-[13.5rem_minmax(0,1fr)] lg:items-start lg:gap-10">
          <nav aria-label="Settings sections" className="lg:sticky lg:top-24">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              This workspace
            </p>
            <a
              href="#connectors"
              className="flex items-center gap-2 rounded-md border border-primary/20 bg-secondary px-3 py-2 text-sm font-medium text-secondary-foreground"
            >
              <Plug className="size-4 text-primary" />
              Connectors
            </a>
          </nav>

          <ConnectorsSection />
        </div>
      </main>
      <WorkspaceFooter />
    </PageShell>
  );
}
