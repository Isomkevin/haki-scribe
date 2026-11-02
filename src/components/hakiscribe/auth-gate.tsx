import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Loader2 } from "lucide-react";
import { currentSession } from "@/lib/auth";

/**
 * Private pages render only for a signed-in user. The check runs after
 * hydration because the session lives in the browser, never on the server.
 * Optional `fallback` is what SSR/crawlers see during the check (and what
 * unauthenticated users briefly see before redirect).
 */
export function RequireAuth({
  children,
  fallback,
}: {
  children: ReactNode;
  fallback?: ReactNode;
}) {
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
      fallback ?? (
        <div className="flex min-h-[60vh] items-center justify-center text-muted-foreground">
          <Loader2 className="mr-2 size-4 animate-spin" aria-hidden />
          <span className="text-sm">Checking your sign-in…</span>
        </div>
      )
    );
  }
  return <>{children}</>;
}
