import { Link } from "@tanstack/react-router";
import { LockKeyhole, Scale } from "lucide-react";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="inline-flex items-center gap-2.5" aria-label="HakiScribe home">
      <span className="grid size-9 place-items-center rounded-md bg-primary text-primary-foreground">
        <Scale className="size-5" strokeWidth={1.8} />
      </span>
      <span className="font-serif text-xl font-semibold text-foreground">
        Haki<span className="text-primary">Scribe</span>
      </span>
      {!compact && <span className="hidden text-xs text-muted-foreground sm:inline">by HakiChain</span>}
    </Link>
  );
}

export function TrustLine({ className = "" }: { className?: string }) {
  return (
    <div className={`inline-flex items-center gap-2 text-xs text-muted-foreground ${className}`}>
      <LockKeyhole className="size-3.5 text-primary" />
      <span>Not used to train models · Kenya DPA-aligned</span>
    </div>
  );
}