import { Link } from "@tanstack/react-router";
import { LockKeyhole, Scale, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

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
    <Dialog>
      <DialogTrigger asChild>
        <button
          type="button"
          className={cn("inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground", className)}
        >
          <LockKeyhole className="size-3.5 text-primary" />
          <span>Not used to train models · Kenya DPA-aligned</span>
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-serif">How this record is treated</DialogTitle>
          <DialogDescription>
            Privilege and the Kenya Data Protection Act decide what a model may see. You stay in control.
          </DialogDescription>
        </DialogHeader>
        <ul className="space-y-3 text-sm leading-6 text-foreground">
          <li>Live captions and analysis use your API keys. HakiScribe does not train foundation models on your sessions.</li>
          <li>Redacted lines stay on the record for you, and are excluded from detection and generation.</li>
          <li>External company research (Exa) is labelled and never treated as something said in the room.</li>
          <li>Generated work stays local until you choose to send it to connected tools. Nothing is auto-filed or auto-sent.</li>
        </ul>
      </DialogContent>
    </Dialog>
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
