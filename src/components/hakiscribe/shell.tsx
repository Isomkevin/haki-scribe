import { Link } from "@tanstack/react-router";
import { ArrowLeft, Headphones, LogOut, Mic, Scale, Settings2 } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { currentSession, signOut } from "@/lib/auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { SessionStatus } from "@/lib/hakiscribe";
import { Brand, SecureBadge } from "./brand";
import { InstallAppButton } from "./pwa-register";

/** Only appears once a session exists in this browser. */
function SignOutButton() {
  const [signedIn, setSignedIn] = useState(false);
  useEffect(() => setSignedIn(Boolean(currentSession())), []);
  if (!signedIn) return null;
  return (
    <Button
      variant="ghost"
      size="sm"
      className="text-muted-foreground"
      onClick={() => {
        signOut();
        window.location.assign("/");
      }}
    >
      <LogOut />
      <span className="hidden sm:inline">Sign out</span>
    </Button>
  );
}

export function PageShell({ children, back }: { children: ReactNode; back?: boolean }) {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-background paper-grain">
      <header className="sticky top-0 z-30 border-b border-border/80 bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-[4.25rem] max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
          {back ? (
            <Link
              to="/"
              className="inline-flex min-w-0 items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              <span aria-hidden className="grid size-8 place-items-center rounded-md border border-border bg-card">
                <ArrowLeft className="size-4" />
              </span>
              <span className="hidden sm:inline">Home</span>
            </Link>
          ) : (
            <Brand />
          )}
          {back && <Brand compact />}
          <div className="flex shrink-0 items-center gap-1 sm:gap-2">
            {back && (
              <>
                <InstallAppButton compact className="hidden h-8 px-2 text-muted-foreground sm:inline-flex" />
                <Button asChild variant="ghost" size="sm" className="text-muted-foreground">
                  <Link
                    to="/settings"
                    activeProps={{ className: "bg-accent text-foreground" }}
                    aria-label="Settings"
                  >
                    <Settings2 />
                    <span className="hidden sm:inline">Settings</span>
                  </Link>
                </Button>
              </>
            )}
            <SignOutButton />
            <SecureBadge />
          </div>
        </div>
        <div className="gold-rule" />
      </header>
      {children}
    </div>
  );
}

export function SectionEyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">{children}</p>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  action,
}: {
  eyebrow: string;
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 grid grid-cols-[minmax(0,1fr)_auto] items-end gap-3 sm:mb-7">
      <div className="min-w-0">
        <SectionEyebrow>{eyebrow}</SectionEyebrow>
        <h2 className="mt-2 font-serif text-2xl font-semibold sm:text-3xl">{title}</h2>
      </div>
      {action}
    </div>
  );
}

const statusStyles: Record<SessionStatus, string> = {
  recording: "border-action/30 bg-action/10 text-action",
  processing: "border-border bg-muted text-muted-foreground",
  ready: "border-primary/20 bg-secondary text-secondary-foreground",
  exported: "border-success-foreground/20 bg-success text-success-foreground",
};

export function StatusBadge({ status }: { status: SessionStatus }) {
  return (
    <Badge variant="outline" className={cn("capitalize", statusStyles[status])}>
      {status}
    </Badge>
  );
}

export function SourceIcon({ source, className }: { source: "mic" | "omi"; className?: string }) {
  const Icon = source === "mic" ? Mic : Headphones;
  return <Icon className={className} />;
}

export function FlowProgress({ current, labels }: { current: number; labels: string[] }) {
  return (
    <ol className="mb-7 grid grid-cols-3 gap-1.5 sm:mb-8 sm:gap-2" aria-label="Session review progress">
      {labels.map((label, index) => {
        const step = index + 1;
        const active = step === current;
        const done = step < current;
        return (
          <li
            key={label}
            className={cn(
              "min-w-0 rounded-lg border px-2 py-2.5 sm:px-3",
              active && "border-primary bg-secondary/70",
              done && "border-border bg-card",
              !active && !done && "border-transparent bg-muted/60 text-muted-foreground",
            )}
          >
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Step {step}
            </p>
            <p className={cn("mt-0.5 truncate text-xs font-medium sm:text-sm", active && "text-primary")}>{label}</p>
          </li>
        );
      })}
    </ol>
  );
}

export function WorkspaceFooter() {
  return (
    <footer className="mt-16 border-t border-border bg-card/60">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-7 sm:flex-row sm:items-center sm:justify-between sm:px-6 sm:py-8">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid size-9 place-items-center rounded-md bg-primary text-primary-foreground">
            <Scale className="size-4" />
          </span>
          <div className="min-w-0">
            <p className="font-serif text-lg font-semibold">Leave the room with the work begun.</p>
            <p className="text-xs text-muted-foreground">A listening instrument of HakiChain · Nairobi</p>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">African languages · code-switch · privilege stays in the room</p>
      </div>
    </footer>
  );
}
