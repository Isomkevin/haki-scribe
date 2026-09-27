import { Link } from "@tanstack/react-router";
import { LockKeyhole, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import logoAsset from "@/assets/hakiscribe-logo.png.asset.json";
import iconAsset from "@/assets/hakiscribe-icon.png.asset.json";
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
    <Link to="/" className="inline-flex items-center" aria-label="HakiScribe home">
      <img
        src={compact ? iconAsset.url : logoAsset.url}
        alt="HakiScribe"
        className={cn("w-auto object-contain", compact ? "h-9" : "h-12")}
      />
    </Link>
  );
}

export function BrandIcon({ className = "" }: { className?: string }) {
  return <img src={iconAsset.url} alt="" className={cn("object-contain", className)} aria-hidden />;
}

export function TrustLine({ className = "" }: { className?: string }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground",
            className,
          )}
        >
          <LockKeyhole className="size-3.5 text-primary" />
          <span>Not used to train models · GDPR compliant</span>
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-serif">How this record is treated</DialogTitle>
          <DialogDescription>
            Privilege, GDPR and respective Juristiction Data protections laws decide what a model
            may see. You stay in control.
          </DialogDescription>
        </DialogHeader>
        <ul className="space-y-3 text-sm leading-6 text-foreground">
          <li>
            Live captions and analysis use your API keys. HakiScribe does not train foundation
            models on your sessions.
          </li>
          <li>
            Redacted lines stay on the record for you, and are excluded from detection and
            generation.
          </li>
          <li>
            External company research (Exa) is labelled and never treated as something said in the
            room.
          </li>
          <li>
            Generated work stays local until you choose to send it to connected tools. Nothing is
            auto-filed or auto-sent.
          </li>
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
