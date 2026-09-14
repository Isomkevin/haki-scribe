import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Loader2 } from "lucide-react";
import { currentSession } from "@/lib/auth";

/**
 * Private pages render only for a signed-in user. The check runs after
 * hydration because the session lives in the browser, never on the server.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [state, setState] = useState<"checking" | "allowed">("checking");

  useEffect(() => {
    if (currentSession()) {
      setState("allowed");
      return;
    }
    const next = `${window.location.pathname}${window.location.search}`;
    void navigate({ to: "/login", search: { next }, replace: true });
  }, [navigate]);

  if (state !== "allowed") {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 size-4 animate-spin" aria-hidden />
        <span className="text-sm">Checking your sign-in…</span>
      </div>
    );
  }
  return <>{children}</>;
}
