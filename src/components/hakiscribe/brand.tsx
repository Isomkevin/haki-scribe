import { Link } from "@tanstack/react-router";
import { LockKeyhole, Scale, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="inline-flex items-center gap-2.5" aria-label="HakiScribe home">
      <span className="grid size-9 place-items-center rounded-md bg-primary text-primary-foreground shadow-sm">
        <Scale className="size-5" strokeWidth={1.8} />
      </span>
      <span className="leading-none">
        <span className="block font-serif text-xl font-semibold tracking-tight text-foreground">
          Haki<span className="text-primary">Scribe</span>
        </span>
        {!compact && (
          <span className="mt-0.5 hidden text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground sm:block">
            by HakiChain
          </span>
        )}
      </span>
    </Link>
  );
}

export function TrustLine({ className = "" }: { className?: string }) {
  return (
    <div className={cn("inline-flex items-center gap-2 text-xs text-muted-foreground", className)}>
      <LockKeyhole className="size-3.5 text-primary" />
      <span>Not used to train models · Kenya DPA-aligned</span>
    </div>
  );
}

export function SecureBadge({ className = "" }: { className?: string }) {
  return (
    <div
      className={cn(
        "hidden items-center gap-2 rounded-full border border-border bg-card/80 px-3 py-1.5 text-xs text-muted-foreground sm:inline-flex",
        className,
      )}
    >
      <ShieldCheck className="size-3.5 text-primary" />
      Secure legal workspace
    </div>
  );
}
