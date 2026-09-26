import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  ArrowLeft,
  Check,
  LockKeyhole,
  Loader2,
  Mic,
  RefreshCw,
  Scale,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  DEMO_CREDENTIALS_QUERY_KEY,
  FALLBACK_DEMO_CREDENTIALS,
  friendlyErrorMessage,
  hakiApi,
  hasApiConfiguration,
  productionAuthApi,
  productionAuthEnabled,
  type DemoCredentials,
  warmWorkspace,
} from "@/lib/hakiscribe";
import { signIn } from "@/lib/auth";
import legalRoomImage from "@/assets/hakiscribe-legal-room.jpg";
import { Brand, TrustLine } from "./brand";

const trustPoints = [
  "Privilege stays in the room until you approve work",
  "Sessions and drafts live behind this sign-in",
  "Not used to train models · GDPR-aligned",
];

const SLOW_WAKE_MS = 2500;

function resolveDemoCredentials(data: DemoCredentials | undefined): DemoCredentials | null {
  if (data?.enabled && data.email && data.password) return data;
  if (hasApiConfiguration) return FALLBACK_DEMO_CREDENTIALS;
  return null;
}

export function LoginPage({ next }: { next?: string | undefined }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [slowWake, setSlowWake] = useState(false);
  const [recoveryReady, setRecoveryReady] = useState(false);
  const [forgotMode, setForgotMode] = useState(false);

  const demo = useQuery({
    queryKey: DEMO_CREDENTIALS_QUERY_KEY,
    queryFn: hakiApi.demoCredentials,
    enabled: hasApiConfiguration && !productionAuthEnabled,
    retry: 4,
    retryDelay: (attempt) => Math.min(1500 * 2 ** attempt, 12_000),
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    if (!hasApiConfiguration || productionAuthEnabled) return;
    void warmWorkspace();
  }, []);

  useEffect(() => {
    if (!demo.isLoading && !demo.isFetching) {
      setSlowWake(false);
      return;
    }
    const timer = window.setTimeout(() => setSlowWake(true), SLOW_WAKE_MS);
    return () => window.clearTimeout(timer);
  }, [demo.isLoading, demo.isFetching]);

  useEffect(() => {
    if (!productionAuthEnabled || typeof window === "undefined") return;
    const values = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const access_token = values.get("access_token");
    const refresh_token = values.get("refresh_token");
    if (!access_token || !refresh_token) return;
    void productionAuthApi
      .establishRecoverySession({ access_token, refresh_token, expires_in: Number(values.get("expires_in")) || undefined })
      .then(() => {
        window.history.replaceState({}, document.title, window.location.pathname);
        setPassword("");
        setRecoveryReady(true);
      })
      .catch(() => setError("This password-reset link is invalid or has expired. Request a new one."));
  }, []);

  const login = useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      productionAuthEnabled ? productionAuthApi.login(body) : hakiApi.login(body),
    onSuccess: (data) => {
      if (productionAuthEnabled) {
        const production = data as Awaited<ReturnType<typeof productionAuthApi.login>>;
        signIn({ token: "", user: { email: production.email || email, name: production.email || email } });
      } else {
        const demoSession = data as Awaited<ReturnType<typeof hakiApi.login>>;
        signIn({ token: demoSession.token, user: demoSession.user });
      }
      const target = next && next.startsWith("/") ? next : "/new";
      window.location.assign(target);
    },
    onError: (err: Error) => {
      const message = friendlyErrorMessage(
        err,
        "That email and password did not match an account.",
      );
      const waking =
        /couldn’t connect|could not connect|unreachable|timed out|timeout|failed to fetch/i.test(
          message,
        );
      setError(
        waking
          ? `${message} If this is your first visit, the workspace may still be waking up — wait a moment and try again.`
          : message,
      );
    },
  });

  const passwordUpdate = useMutation({
    mutationFn: (nextPassword: string) => productionAuthApi.updatePassword(nextPassword),
    onSuccess: () => {
      window.location.assign("/login");
    },
    onError: (err: Error) => setError(friendlyErrorMessage(err, "We could not update your password. Try again.")),
  });

  const passwordReset = useMutation({
    mutationFn: (address: string) => productionAuthApi.requestPasswordReset(address),
    onSuccess: (data) => setNotice(data.message),
    onError: (err: Error) => setError(friendlyErrorMessage(err, "We could not request a password reset. Try again.")),
  });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (recoveryReady) {
      passwordUpdate.mutate(password);
      return;
    }
    if (forgotMode) {
      passwordReset.mutate(email);
      return;
    }
    login.mutate({ email, password });
  }

  function useDemo() {
    const creds = resolveDemoCredentials(demo.data);
    if (!creds?.email || !creds.password) return;
    setEmail(creds.email);
    setPassword(creds.password);
    setError(null);
    login.mutate({ email: creds.email, password: creds.password });
  }

  const demoDisabledByServer = demo.isSuccess && demo.data?.enabled === false;
  const showDemoPanel = hasApiConfiguration && !productionAuthEnabled && !demoDisabledByServer;
  const demoReady = Boolean(resolveDemoCredentials(demo.data));
  const demoWaking =
    showDemoPanel && (demo.isLoading || demo.isFetching || demo.isError || slowWake);
  const demoCanSubmit = demoReady && !login.isPending;

  return (
    <div className="relative min-h-svh overflow-x-hidden bg-background paper-grain">
      <div className="grid min-h-svh lg:grid-cols-[minmax(0,1.05fr)_minmax(22rem,0.95fr)]">
        {/* Brand panel — secondary on mobile, hero presence on desktop */}
        <aside className="relative isolate order-2 overflow-hidden border-t border-border lg:order-1 lg:min-h-svh lg:border-t-0 lg:border-r">
          <div className="absolute inset-0 bg-intelligence">
            <img
              src={legalRoomImage}
              alt=""
              width={1600}
              height={900}
              className="size-full object-cover object-[58%_center] opacity-40 lg:opacity-55"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-intelligence via-intelligence/95 to-intelligence/70 lg:bg-gradient-to-r lg:from-intelligence lg:via-intelligence/90 lg:to-intelligence/35" />
          </div>

          <div className="relative z-10 flex h-full flex-col justify-between gap-8 px-5 py-8 text-intelligence-foreground sm:px-8 sm:py-10 lg:gap-10 lg:px-10 lg:py-14 xl:px-14">
            <div className="hidden lg:block">
              <Link
                to="/"
                className="inline-flex items-center gap-2.5 text-intelligence-foreground"
                aria-label="HakiScribe home"
              >
                <span className="grid size-10 place-items-center rounded-md bg-intelligence-accent text-intelligence">
                  <Scale className="size-5" strokeWidth={1.8} />
                </span>
                <span className="leading-none">
                  <span className="block font-serif text-xl font-semibold tracking-tight">
                    Haki<span className="text-intelligence-accent">Scribe</span>
                  </span>
                  <span className="mt-0.5 block text-[11px] font-medium uppercase tracking-[0.16em] text-intelligence-muted">
                    by HakiChain
                  </span>
                </span>
              </Link>
            </div>

            <div className="max-w-lg animate-ink-rise">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-intelligence-accent">
                Private legal workspace
              </p>
              <h2 className="mt-3 font-serif text-2xl font-semibold leading-[1.12] tracking-tight sm:text-3xl lg:text-5xl">
                Capture what matters.{" "}
                <em className="italic text-intelligence-accent">
                  Leave with your Legal work ready.
                </em>
              </h2>
              <p className="mt-3 max-w-md text-sm leading-6 text-intelligence-muted sm:mt-4 sm:text-base sm:leading-7">
                Sign in to open sessions, verify the record, protect privilege, and choose the
                source-traceable work HakiScribe prepares.
              </p>

              <ul className="mt-5 space-y-2.5 sm:mt-7 sm:space-y-3">
                {trustPoints.map((point) => (
                  <li
                    key={point}
                    className="flex items-start gap-3 text-sm leading-6 text-intelligence-foreground/90"
                  >
                    <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-intelligence-accent/15 text-intelligence-accent">
                      <Check className="size-3" strokeWidth={2.5} />
                    </span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs text-intelligence-muted sm:gap-3">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-intelligence-border bg-intelligence/50 px-3 py-1.5">
                <Mic className="size-3.5 text-intelligence-accent" />
                Mic or Omi
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-intelligence-border bg-intelligence/50 px-3 py-1.5">
                <ShieldCheck className="size-3.5 text-intelligence-accent" />
                Secure workspace
              </span>
            </div>
          </div>
        </aside>

        {/* Form column — first on mobile */}
        <main className="order-1 flex flex-col lg:order-2">
          <header className="flex items-center justify-between gap-3 border-b border-border/80 px-4 py-4 sm:px-6 lg:px-8">
            <div className="min-w-0 lg:hidden">
              <Brand compact />
            </div>
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              <span className="grid size-8 place-items-center rounded-md border border-border bg-card">
                <ArrowLeft className="size-4" />
              </span>
              <span className="hidden sm:inline">Back to landing</span>
              <span className="sm:hidden">Home</span>
            </Link>
          </header>
          <div className="gold-rule" />

          <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
            <div className="animate-ink-rise">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
                Sign in
              </p>
              <h1 className="mt-2 font-serif text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                Enter your workspace
              </h1>
              <p className="mt-3 text-sm leading-6 text-muted-foreground sm:text-base sm:leading-7">
                Recordings, transcripts, and drafted documents stay behind this gate.
              </p>
            </div>

            <form
              onSubmit={submit}
              className="desk-card mt-8 overflow-hidden rounded-2xl border border-border"
              noValidate
            >
              <div className="h-1 bg-gradient-to-r from-primary via-action to-primary" />
              <div className="space-y-5 p-5 sm:p-6">
                {!recoveryReady ? <div className="space-y-2">
                  <Label
                    htmlFor="login-email"
                    className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground"
                  >
                    Email
                  </Label>
                  <Input
                    id="login-email"
                    type="email"
                    inputMode="email"
                    autoComplete="username"
                    autoCapitalize="none"
                    autoCorrect="off"
                    spellCheck={false}
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="advocate@firm.co.ke"
                    required
                    className="h-12 bg-background text-base"
                  />
                </div> : null}

                {!forgotMode ? <div className="space-y-2">
                  <Label
                    htmlFor="login-password"
                    className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground"
                  >
                    {recoveryReady ? "New password" : "Password"}
                  </Label>
                  <Input
                    id="login-password"
                    type="password"
                    autoComplete={recoveryReady ? "new-password" : "current-password"}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    className="h-12 bg-background text-base"
                  />
                </div> : null}

                {productionAuthEnabled && !recoveryReady && !forgotMode ? (
                  <button
                    type="button"
                    className="text-left text-sm font-medium text-primary hover:underline"
                    onClick={() => { setForgotMode(true); setError(null); setNotice(null); }}
                  >
                    Forgot your password?
                  </button>
                ) : null}

                {forgotMode ? (
                  <button
                    type="button"
                    className="text-left text-sm font-medium text-primary hover:underline"
                    onClick={() => { setForgotMode(false); setError(null); setNotice(null); }}
                  >
                    Back to sign in
                  </button>
                ) : null}

                {error ? (
                  <div
                    role="alert"
                    className="rounded-lg border border-destructive/25 bg-destructive/5 px-3 py-2.5 text-sm leading-6 text-destructive"
                  >
                    {error}
                  </div>
                ) : null}

                {notice ? (
                  <div role="status" className="rounded-lg border border-success/30 bg-success/10 px-3 py-2.5 text-sm leading-6 text-success-foreground">
                    {notice}
                  </div>
                ) : null}

                <Button
                  type="submit"
                  variant="warm"
                  size="lg"
                  className="h-12 w-full text-base"
                  disabled={login.isPending || passwordUpdate.isPending || passwordReset.isPending || (!forgotMode && !password) || (!recoveryReady && !email.trim())}
                >
                  {login.isPending || passwordUpdate.isPending || passwordReset.isPending ? (
                    <>
                      <Loader2 className="size-4 animate-spin" aria-hidden />
                      {recoveryReady ? "Updating password…" : forgotMode ? "Sending reset link…" : "Signing in…"}
                    </>
                  ) : (
                    recoveryReady ? <>
                      <LockKeyhole className="size-4" aria-hidden />
                      Update password
                    </> : forgotMode ? <>
                      <LockKeyhole className="size-4" aria-hidden />
                      Send reset link
                    </> : <>
                      <LockKeyhole className="size-4" aria-hidden />
                      Sign in
                    </>
                  )}
                </Button>

                {showDemoPanel ? (
                  <div className="rounded-xl border border-dashed border-border bg-muted/35 p-4">
                    <p className="text-xs leading-5 text-muted-foreground">
                      <span className="font-semibold text-foreground">Temporary demo access.</span>{" "}
                      Shared for judging.
                    </p>

                    {demoWaking && !demo.isSuccess ? (
                      <p className="mt-2 text-xs leading-5 text-muted-foreground" role="status">
                        {slowWake || demo.isError
                          ? "The workspace is waking up — first visit can take up to a minute. You can still use demo credentials; sign-in will wait for the service."
                          : "Connecting to the workspace…"}
                      </p>
                    ) : null}

                    <Button
                      type="button"
                      variant="outline"
                      className="mt-3 h-11 w-full"
                      onClick={useDemo}
                      disabled={!demoCanSubmit}
                    >
                      {login.isPending ? (
                        <>
                          <Loader2 className="size-4 animate-spin" aria-hidden />
                          Signing in…
                        </>
                      ) : (
                        <>
                          <ShieldCheck className="size-4" aria-hidden />
                          Use demo credentials
                        </>
                      )}
                    </Button>

                    {(demo.isError || (slowWake && !demo.isSuccess)) && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="mt-2 h-9 w-full text-xs"
                        onClick={() => void demo.refetch()}
                        disabled={demo.isFetching}
                      >
                        <RefreshCw
                          className={demo.isFetching ? "size-3.5 animate-spin" : "size-3.5"}
                          aria-hidden
                        />
                        Retry connection
                      </Button>
                    )}
                  </div>
                ) : null}
              </div>
            </form>

            <div className="mt-6 space-y-3">
              <TrustLine className="rounded-full border border-border bg-card/80 px-3 py-1.5" />
              <p className="text-xs leading-5 text-muted-foreground">
                Need a practice account? Ask your HakiChain administrator — this workspace is
                invite-only.
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
