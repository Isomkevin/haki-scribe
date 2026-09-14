import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

declare global {
  interface WindowEventMap {
    beforeinstallprompt: BeforeInstallPromptEvent;
  }
}

let deferredInstallPrompt: BeforeInstallPromptEvent | null = null;
const installListeners = new Set<(event: BeforeInstallPromptEvent | null) => void>();

function notifyInstallListeners(event: BeforeInstallPromptEvent | null) {
  for (const listener of installListeners) listener(event);
}

export function PwaRegister() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const onBeforeInstall = (event: BeforeInstallPromptEvent) => {
      event.preventDefault();
      deferredInstallPrompt = event;
      notifyInstallListeners(event);
    };

    window.addEventListener("beforeinstallprompt", onBeforeInstall);

    if (!("serviceWorker" in navigator) || !import.meta.env.PROD) {
      return () => window.removeEventListener("beforeinstallprompt", onBeforeInstall);
    }

    let refreshing = false;
    const onControllerChange = () => {
      if (refreshing) return;
      refreshing = true;
      window.location.reload();
    };

    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);

    void navigator.serviceWorker
      .register("/sw.js")
      .then((registration) => {
        const promptRefresh = () => {
          toast.message("Update available", {
            description: "A newer HakiScribe shell is ready.",
            action: {
              label: "Refresh",
              onClick: () => {
                registration.waiting?.postMessage("SKIP_WAITING");
              },
            },
            duration: 12_000,
          });
        };

        if (registration.waiting) promptRefresh();

        registration.addEventListener("updatefound", () => {
          const worker = registration.installing;
          if (!worker) return;
          worker.addEventListener("statechange", () => {
            if (worker.state === "installed" && navigator.serviceWorker.controller) {
              promptRefresh();
            }
          });
        });
      })
      .catch(() => {
        // Registration failures should not block the legal workspace.
      });

    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
    };
  }, []);

  return null;
}

export function useInstallPrompt() {
  const [promptEvent, setPromptEvent] = useState<BeforeInstallPromptEvent | null>(deferredInstallPrompt);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const sync = (event: BeforeInstallPromptEvent | null) => setPromptEvent(event);
    installListeners.add(sync);
    setPromptEvent(deferredInstallPrompt);

    const media = window.matchMedia("(display-mode: standalone)");
    const syncInstalled = () => setInstalled(media.matches || ("standalone" in navigator && Boolean((navigator as Navigator & { standalone?: boolean }).standalone)));
    syncInstalled();
    media.addEventListener?.("change", syncInstalled);

    return () => {
      installListeners.delete(sync);
      media.removeEventListener?.("change", syncInstalled);
    };
  }, []);

  const install = async () => {
    const event = promptEvent ?? deferredInstallPrompt;
    if (!event) return false;
    await event.prompt();
    const choice = await event.userChoice;
    deferredInstallPrompt = null;
    setPromptEvent(null);
    notifyInstallListeners(null);
    return choice.outcome === "accepted";
  };

  return {
    canInstall: Boolean(promptEvent) && !installed,
    installed,
    install,
  };
}

export function InstallAppButton({ className, compact = false }: { className?: string; compact?: boolean }) {
  const { canInstall, installed, install } = useInstallPrompt();
  if (installed) {
    if (compact) return null;
    return (
      <p className="text-sm text-muted-foreground">
        HakiScribe is installed on this device.
      </p>
    );
  }
  if (!canInstall) {
    if (compact) return null;
    return (
      <p className="text-sm leading-6 text-muted-foreground">
        On supported browsers, use the browser menu to install HakiScribe, or Add to Home Screen on iPhone.
      </p>
    );
  }
  return (
    <Button
      type="button"
      variant="outline"
      size={compact ? "sm" : "default"}
      className={className}
      onClick={() => {
        void install().then((accepted) => {
          if (accepted) toast.success("HakiScribe installed");
        });
      }}
    >
      <Download /> Install app
    </Button>
  );
}
